import html
import traceback
import ujson

from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from src.base.config import config
from src.base.utils.base import Utils
from src.base.logger import Log

utils = Utils(config)


def start(update: Update, _: CallbackContext) -> None:
    user = update.effective_user
    Log.info("start命令请求 user %s id %s" % (user["username"], user["id"]))
    message = "✿✿ヽ（°▽°）ノ✿ hi！%s  \n" \
              "这里是GenshinPicBed机器人"
    update.message.reply_markdown_v2(message % user.mention_markdown_v2())


def test(update: Update, _: CallbackContext) -> None:
    user = update.effective_user
    if not utils.IfOwner(user["id"]):
        return
    Log.info("test命令请求 user %s" % user["username"])
    update.message.reply_text("pass")


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
        message = "好啊嗷 ✿✿ヽ（°▽°）ノ✿   \n" \
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


def error_handler(update: object, context: CallbackContext) -> None:
    """
    记录错误并发送消息通知开发人员。
    Log the error and send a telegram message to notify the developer.
    """
    Log.error(msg="处理函数时发生异常:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f'<b>处理函数时发生异常</b> \n'
        f'Exception while handling an update \n'
        f'<pre>update = {html.escape(ujson.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    channel_id = config.TELEGRAM["channel"]["LOG"]["char_id"]
    context.bot.send_message(chat_id=channel_id, text=message, parse_mode=ParseMode.HTML)
