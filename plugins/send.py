from typing import Iterable

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from src.base.logger import Log
from src.base.config import config
from src.base.model.newartwork import ArtworkImage, ArtworkInfo
from src.base.utils.base import Utils
from src.base.utils.markdown import markdown_escape
from src.production.service.service import SendService


class SendHandler:
    ONE, TWO, THREE, FOUR = range(4)

    def __init__(self, send_service: SendService = None):
        self.utils = Utils(config)
        self.send_service = send_service

    def send_command(self, update: Update, context: CallbackContext) -> int:
        user = update.effective_user
        Log.info("send命令请求 user %s id %s" % (user["username"], user["id"]))
        if not self.utils.IfAdmin(user["id"]):
            update.message.reply_text("你不是BOT管理员，不能使用此命令！")
            return ConversationHandler.END
        message = "✿✿ヽ（°▽°）ノ✿ 你好！ %s ，欢迎 \n" \
                  "当前直投只支持Twitter \n" \
                  "只需复制URL回复即可 \n" \
                  "退出投稿只需回复退出" % (user["username"])
        reply_keyboard = [['退出']]
        update.message.reply_text(text=message,
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.ONE

    def get_info(self, update: Update, context: CallbackContext) -> int:
        if update.message.text == "退出":
            update.message.reply_text(text="退出投稿", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        if update.message.text is None:
            update.message.reply_text(text="回复错误", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        artwork_data = self.send_service.get_info(update.message.text)
        if artwork_data is None:
            update.message.reply_text("已经存在数据库或者频道，退出投稿", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        artwork_info, images = artwork_data
        context.chat_data["send_command_artwork_info"] = artwork_info
        context.chat_data["send_command_images_data"] = images
        caption = "Title %s   \n" \
                  "%s   \n" \
                  "Tags %s   \n" \
                  "From [%s](%s)" % (
                      markdown_escape(artwork_info.title),
                      artwork_info.GetStringStat(),
                      markdown_escape(artwork_info.GetStringTags()),
                      artwork_info.site_name,
                      artwork_info.origin_url
                  )
        try:
            if len(images) > 1:
                media = [InputMediaPhoto(media=img_info.data) for img_info in images]
                media = media[:10]
                media[0] = InputMediaPhoto(media=images[0].data, caption=caption,
                                           parse_mode=ParseMode.MARKDOWN_V2)
                update.message.reply_media_group(media, timeout=30)
            elif len(images) == 1:
                photo = images[0].data
                update.message.reply_photo(photo=photo,
                                           caption=caption,
                                           timeout=30,
                                           parse_mode=ParseMode.MARKDOWN_V2)
            else:
                update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())  # excuse?
                return ConversationHandler.END
        except BadRequest as TError:
            update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
            Log.error("encounter error with image caption\n%s" % caption)
            Log.error(TError)
            return ConversationHandler.END
        reply_keyboard = [['SFW', 'NSFW'], ['R18', '退出']]
        message = "请选择你推送到的频道"
        update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.TWO

    def get_channel(self, update: Update, context: CallbackContext) -> int:
        user = update.effective_user
        if update.message.text == "退出":
            update.message.reply_text(text="退出任务", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        try:
            channel_type = update.message.text
            channel_name = config.TELEGRAM["channel"][channel_type]["name"]
            channel_id = config.TELEGRAM["channel"][channel_type]["char_id"]
            context.chat_data["channel_id"] = channel_id
        except KeyError:
            update.message.reply_text(text="发生错误，退出任务", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        update.message.reply_text("你选择的频道名称为 %s 类型为 %s" % (channel_name, channel_type))
        reply_keyboard = [['确认', '取消']]
        message = "请确认推送的频道和作品的信息"
        update.message.reply_text(
            message,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return self.THREE

    def send_message(self, update: Update, context: CallbackContext) -> int:
        update.message.reply_text("正在推送", reply_markup=ReplyKeyboardRemove())
        channel_id = context.chat_data.get("channel_id", -1)
        if update.message.text == "取消":
            update.message.reply_text(text="退出任务", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        artwork_info: ArtworkInfo = context.chat_data["send_command_artwork_info"]
        images: Iterable[ArtworkImage] = context.chat_data["send_command_images_data"]
        caption = "Title %s   \n" \
                  "Tags %s   \n" \
                  "From [%s](%s)" % (
                      markdown_escape(artwork_info.title),
                      markdown_escape(artwork_info.GetStringTags()),
                      artwork_info.site_name,
                      artwork_info.origin_url
                  )
        try:
            if len(images) > 1:
                media = [InputMediaPhoto(media=img_info.data) for img_info in images]
                media = media[:10]
                media[0] = InputMediaPhoto(media=images[0].data, caption=caption,
                                           parse_mode=ParseMode.MARKDOWN_V2)
                context.bot.send_media_group(channel_id, media=media, timeout=30)
            elif len(images) == 1:
                photo = images[0].data
                context.bot.send_photo(channel_id,
                                       photo=photo,
                                       caption=caption,
                                       timeout=30,
                                       parse_mode=ParseMode.MARKDOWN_V2)
            else:
                update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
        except BadRequest as TError:
            update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
            Log.error("encounter error with image caption\n%s" % caption)
            Log.error(TError)
            return ConversationHandler.END
        update.message.reply_text("推送完成", reply_markup=ReplyKeyboardRemove())
        self.send_service.contribute(artwork_info)
        return ConversationHandler.END
