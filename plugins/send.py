from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from src.base.logger import Log
from src.base.config import config
from src.base.utils.base import Utils
from src.base.utils.markdown import markdown_escape
from src.production.pixiv import PixivService
from src.production.pixiv.downloader import PixivDownloader
from src.production.contribute import Contribute
from src.production.sites.twitter.interface import ExtractTid


class ContributeHandler:
    ONE, TWO, THREE, FOUR = range(4)

    def __init__(self, pixiv: PixivService = None):
        self.downloader = PixivDownloader(cookie=config.PIXIV["cookie"])
        self.contribute = Contribute()
        self.pixiv = pixiv
        self.utils = Utils(config)

    def send_command(self, update: Update, _: CallbackContext) -> int:
        user = update.effective_user
        Log.info("send命令请求 user %s id %s" % (user["username"], user["id"]))
        if not self.utils.IfAdmin(user["id"]):
            update.message.reply_text("你不是BOT管理员，不能使用此命令！")
            return ConversationHandler.END
        message = "✿✿ヽ（°▽°）ノ✿ 你好！ %s ，欢迎 \n" \
                  "当前直投稿只支持Twitter \n" \
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
        else:
            message = "获取作品信息失败，请检连接或者ID是否有误"
            update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
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
