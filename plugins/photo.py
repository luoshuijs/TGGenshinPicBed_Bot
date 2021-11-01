from saucenao_api.errors import UnknownServerError
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from logger import Log
from config import config
from utils.base import Utils
from utils.markdown import markdown_escape
from service import SiteService, AuditService
from saucenao_api import SauceNao


class PhotoHandlerData:
    def __int__(self):
        self.photo_data: bytes = b""


class PhotoHandler:
    ONE, TWO, THREE, FOUR = range(10600, 10604)

    def __init__(self, site_service: SiteService = None, audit_service: AuditService = None):
        self.utils = Utils(config)
        self.site_service = site_service
        self.audit_service = audit_service
        self.saucenao_apikey = config.SAUCENAO["apikey"]
        self.sauce = None
        if self.saucenao_apikey != "":
            self.sauce = SauceNao(self.saucenao_apikey)

    def start(self, update: Update, context: CallbackContext) -> int:
        user = update.effective_user
        Log.info("图片查找命令请求 user %s id %s" % (user["username"], user["id"]))
        user = update.effective_user
        if user is None:
            return ConversationHandler.END
        if not self.utils.IfAdmin(user["id"]):
            return ConversationHandler.END
        if update.message.chat.type != "private":
            return ConversationHandler.END
        if self.sauce is None:
            return ConversationHandler.END
        photo_handler_data = context.chat_data.get("photo_handler_data")
        if photo_handler_data is None:
            photo_handler_data = PhotoHandlerData()
            context.chat_data["photo_handler_data"] = photo_handler_data
        photo_file = update.message.photo[0].get_file()
        photo_handler_data.photo_data = photo_file.download_as_bytearray()
        reply_keyboard = [['继续', '退出']]
        update.message.reply_text("获取图片成功，是否搜索图片",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                                   one_time_keyboard=True))
        return self.ONE

    def get(self, update: Update, context: CallbackContext) -> int:
        photo_handler_data: PhotoHandlerData = context.chat_data.get("photo_handler_data")
        if update.message.text == "退出":
            update.message.reply_text('退出搜索', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        update.message.reply_text("正在搜索图片")
        photo_data = photo_handler_data.photo_data
        try:
            results = self.sauce.from_file(photo_data)
        except UnknownServerError as error:
            update.message.reply_text("saucenao_api抛出UnknownServerError错误，获取图片信息失败")
            return ConversationHandler.END
        artwork_data = None
        if bool(results):
            for result in results:
                if result.similarity >= 50:
                    if len(result.urls) == 0:
                        continue
                    url = result.urls[0]
                    Log.info("图片搜索结果 title %s url %s" % (result.title, url))
                    artwork_data = self.site_service.get_info_by_url(url)
                    if artwork_data.is_error:
                        continue
        else:
            update.message.reply_text("搜索失败")
            return ConversationHandler.END
        update.message.reply_text("正在获取图片信息")
        if artwork_data is None or artwork_data.is_error:
            update.message.reply_text("无法找到对应的图片，获取图片信息失败")
            return ConversationHandler.END
        artwork_info = artwork_data.artwork_info
        artwork_image = artwork_data.artwork_image
        audit_info = self.audit_service.get_audit_info(artwork_info)
        caption = "Title %s   \n" \
                  "%s   \n" \
                  "Tags %s   \n" \
                  "From [%s](%s)" % (
                      markdown_escape(artwork_info.title),
                      artwork_info.GetStringStat(),
                      markdown_escape(artwork_info.GetStringTags(filter_character_tags=True)),
                      artwork_info.site_name,
                      artwork_info.origin_url
                  )
        try:
            if len(artwork_image) > 1:
                media = [InputMediaPhoto(media=img_info.data) for img_info in artwork_image]
                media = media[:10]
                media[0] = InputMediaPhoto(media=artwork_image[0].data, caption=caption,
                                           parse_mode=ParseMode.MARKDOWN_V2)
                update.message.reply_media_group(media, timeout=30)
            elif len(artwork_image) == 1:
                image = artwork_image[0]
                if image.format == "gif":
                    update.message.reply_animation(animation=image.data,
                                                   caption=caption,
                                                   timeout=30,
                                                   parse_mode=ParseMode.MARKDOWN_V2)
                else:
                    update.message.reply_photo(photo=image.data,
                                               caption=caption,
                                               timeout=30,
                                               parse_mode=ParseMode.MARKDOWN_V2)
            else:
                update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())  # excuse?
                return ConversationHandler.END
        except (BadRequest, TypeError) as TError:
            update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
            Log.error("encounter error with image caption\n%s" % caption)
            Log.error(TError)
            return ConversationHandler.END
        update.message.reply_text("获取图片信息完成")
        if audit_info.site == "":
            update.message.reply_text("该作品未推送 使用 /send 回复相应图片推送到频道", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text("该作品已经存在频道上", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
