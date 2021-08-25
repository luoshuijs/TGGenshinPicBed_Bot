from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from src.base.logger import Log
from src.base.config import config
from src.base.utils.base import Utils
from src.base.utils.markdown import markdown_escape
from src.production.sites.twitter.interface import ExtractTid
from src.production.sites.twitter.service import TwitterService


class SendHandler:
    ONE, TWO, THREE, FOUR = range(4)

    def __init__(self, twitter: TwitterService = None):
        self.utils = Utils(config)
        self.twitter = twitter

    def send_command(self, update: Update, _: CallbackContext) -> int:
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
        # 获取作品信息并发送
        if "twitter" in update.message.text:
            tid = ExtractTid(update.message.text)
            if tid is None:
                message = "获取作品信息失败，请检连接或者ID是否有误"
                update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
            artwork_data = self.twitter.contribute_start(tid)
            if artwork_data is None:
                update.message.reply_text("插画信息获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
            artwork_info, images = artwork_data
        else:
            message = "获取作品信息失败，请检连接或者ID是否有误"
            update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
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
        reply_keyboard = [['确认', '取消']]
        message = "请确认作品的信息"
        update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.TWO

    def end(self, update: Update, context: CallbackContext) -> int:
        if update.message.text == "取消":
            update.message.reply_text(text="退出投稿", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        update.message.reply_text('投稿成功！✿✿ヽ（°▽°）ノ✿', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
