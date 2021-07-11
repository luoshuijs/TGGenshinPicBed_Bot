from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler

from src.base.logger import Log

ONE, TWO, THREE, FOUR = range(4)


def contribute(update: Update, _: CallbackContext) -> int:
    user = update.effective_user
    Log.info("contribute命令请求 user %s id %s" % (user["username"], user["id"]))
    message = "✿✿ヽ（°▽°）ノ✿ 你好！ %s ，欢迎投稿 \n" \
              "当前投稿只支持Pixiv \n" \
              "只需复制URL回复即可 \n" \
              "退出投稿只需回复退出" % (user["username"])
    update.message.reply_text(text=message)


def ContributeInfo(update: Update, context: CallbackContext) -> int:
    if update.message.text == "退出":
        update.message.reply_text(text="退出投稿")
        return ConversationHandler.END
    # 获取作品信息并发送
    reply_keyboard = [['确认', '取消']]
    message = "请确认作品的信息"
    update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return ONE


def StartContribute(update: Update, context: CallbackContext) -> int:
    if update.message.text == "取消":
        update.message.reply_text(text="退出投稿")
        return ConversationHandler.END
    # 写入数据库
    update.message.reply_text('投稿成功', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
