import asyncio

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ConversationHandler, CallbackContext

from src.base.config import config
from src.base.logger import Log
from src.base.utils import Utils
from src.production.crawl.pixivdownload import Pixiv


class Download:
    ONE, TWO, THREE = range(3)

    def __init__(self, update: Update):
        self.update = update
        self.loop = asyncio.get_event_loop()
        self.Task_list = []
        self.utils = Utils(config)
        self.pixiv = Pixiv(
            mysql_host=config.MYSQL["host"],
            mysql_port=config.MYSQL["port"],
            mysql_user=config.MYSQL["user"],
            mysql_password=config.MYSQL["pass"],
            mysql_database=config.MYSQL["database"],
            pixiv_cookie=config.PIXIV["cookie"],
            loop=self.loop
        )

    def __del__(self):
        close = [self.pixiv.close()]
        self.loop.run_until_complete(
            asyncio.wait(close)
        )
        self.loop.close()

    def download(self, update: Update, context: CallbackContext) -> int:
        user = update.effective_user
        Log.info("download命令请求 user %s id %s" % (user["username"], user["id"]))
        if not self.utils.IfAdmin(user["id"]):
            update.message.reply_text("你不是BOT管理员，不能使用此命令！")
            return ConversationHandler.END
        reply_keyboard = [['开始', '退出']]
        message = "✿✿ヽ（°▽°）ノ✿ 你好！ %s ，是否执行爬虫" % (user["username"])
        update.message.reply_text(
            message,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return self.ONE

    def start_download(self, update: Update, context: CallbackContext) -> int:
        if update.message.text == "退出":
            update.message.reply_text(text="退出任务")
            return ConversationHandler.END
        context.bot_data["download_chat_id"] = update.message.chat_id
        try:
            update.message.reply_text(text="请耐心等待任务完成")
            run = [self.pixiv.work(self.loop, sleep_time=-1)]
            self.loop.run_until_complete(asyncio.wait(run))
            update.message.reply_text(text="执行成功")
        except BaseException as err:
            Log.error(err)
            update.message.reply_text(text="发生错误，执行失败")
        return ConversationHandler.END
