import re
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler
from telegram.utils.helpers import escape_markdown

from logger import Log
from service import AuditService, SiteService


class ContributeHandler:
    ONE, TWO, THREE, FOUR = range(10400, 10404)
    GENSHIN_REGEX = re.compile(r"(Genshin(Impact)?)|(原神)", re.I)

    def __init__(self, site_service: SiteService = None, audit_service: AuditService = None):
        self.site_service = site_service
        self.audit_service = audit_service

    def contribute_command(self, update: Update, _: CallbackContext) -> int:
        user = update.effective_user
        Log.info("contribute命令请求 user %s id %s" % (user["username"], user["id"]))
        message = "✿✿ヽ（°▽°）ノ✿ 你好！ %s ，欢迎投稿 \n" \
                  "当前投稿只支持Pixiv \n" \
                  "只需复制URL回复即可 \n" \
                  "退出投稿只需回复退出" % (user["username"])
        reply_keyboard = [['退出']]
        update.message.reply_text(text=message,
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.ONE

    def ContributeInfo(self, update: Update, context: CallbackContext) -> int:
        if update.message.text == "退出":
            update.message.reply_text(text="退出投稿", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        artwork_data = self.site_service.contribute_start(update.message.text)
        if artwork_data.is_error:  # 作品存在数据库返回None
            update.message.reply_text("%s，退出投稿" % artwork_data.message, reply_markup=ReplyKeyboardRemove())  #
            return ConversationHandler.END
        artwork_info = artwork_data.artwork_info
        images = artwork_data.artwork_image
        Log.info("用户 %s 请求投稿作品 id: %s" % (update.effective_user.username, artwork_info.artwork_id))
        if artwork_info is None:
            update.message.reply_text("插画信息获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        if ContributeHandler.GENSHIN_REGEX.search(artwork_info.GetStringTags()) is None:
            update.message.reply_text("插画信息TAG不符合投稿要求，退出投稿", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        caption = "Title %s   \n" \
                  "%s \n" \
                  "Tags %s   \n" \
                  "From [%s](%s)" % (
                      escape_markdown(artwork_info.title, version=2),
                      artwork_info.GetStringStat(),
                      escape_markdown(artwork_info.GetStringTags(filter_character_tags=True), version=2),
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
                Log.error("图片获取失败")
                update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())  # excuse?
                return ConversationHandler.END
        except BadRequest as TError:
            update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
            Log.error("encounter error with image caption\n%s" % caption)
            Log.error(TError)
            return ConversationHandler.END
        context.chat_data["contribute_data"] = artwork_info
        reply_keyboard = [['确认', '取消']]
        message = "请确认作品的信息"
        update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.TWO

    def StartContribute(self, update: Update, context: CallbackContext) -> int:
        if update.message.text == "取消":
            update.message.reply_text(text="退出投稿", reply_markup=ReplyKeyboardRemove())
        elif update.message.text == "确认":
            artwork_info = context.chat_data["contribute_data"]
            self.site_service.contribute(artwork_info)
            update.message.reply_text('投稿成功！✿✿ヽ（°▽°）ノ✿', reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text('命令错误，请重新回复')
            return self.TWO
        return ConversationHandler.END
