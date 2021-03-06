from telegram import Update
from telegram.ext import CallbackContext

from config import config
from utils.base import Utils
from logger import Log

utils = Utils(config)


def start(update: Update, _: CallbackContext) -> None:
    user = update.effective_user
    Log.info("start命令请求 user %s id %s" % (user["username"], user["id"]))
    message = "✿✿ヽ（°▽°）ノ✿ hi！%s  \n" \
              "这里是GenshinPicBed机器人"
    update.message.reply_markdown_v2(message % user.mention_markdown_v2())


def help_command(update: Update, _: CallbackContext) -> None:
    user = update.effective_user
    if utils.IfOwner(user["id"]):
        message = "亲爱主人你好啊嗷 ✿✿ヽ（°▽°）ノ✿   \n" \
                  "可以使用一下命令   \n" \
                  "内部命令   \n" \
                  "/examine 进入审核  \n" \
                  "/set 修改图片信息  \n" \
                  "/download 爬取图片  \n" \
                  "/push 推送频道"
    elif utils.IfAdmin(user["id"]):
        message = "你好啊嗷 ✿✿ヽ（°▽°）ノ✿   \n" \
                  "可以使用一下命令   \n" \
                  "内部命令   \n" \
                  "/examine 进入审核  \n" \
                  "/set 修改图片信息  \n" \
                  "/push 推送频道"
    else:
        message = "懒得写.jpg"
    update.message.reply_text(message)


def echo(update: Update, _: CallbackContext) -> None:
    if update.message.MESSAGE_TYPES == "text":
        if update.message.text == "不够色":
            update.message.reply_text("那你来发")


def ping(update: Update, _: CallbackContext) -> None:
    update.message.reply_text("online! ヾ(✿ﾟ▽ﾟ)ノ")


def unknown_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('前面的区域，以后再来探索吧！')


def test(update: Update, _: CallbackContext) -> None:
    """
    单  元  测  试   (dogo)
    """
    user = update.effective_user
    if not utils.IfOwner(user["id"]):
        return
    Log.info("test命令请求 user %s" % user["username"])
    update.message.reply_text("pass")
