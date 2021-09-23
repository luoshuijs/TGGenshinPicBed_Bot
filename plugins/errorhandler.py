import html
import traceback
import ujson
from telegram import Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext
from src.base.config import config
from src.base.logger import Log


def error_handler(update: object, context: CallbackContext) -> None:
    """
    记录错误并发送消息通知开发人员。
    Log the error and send a telegram message to notify the developer.
    """
    Log.error(msg="处理函数时发生异常:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message_1 = (
        f'<b>处理函数时发生异常</b> \n'
        f'Exception while handling an update \n'
        f'<pre>update = {html.escape(ujson.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
    )
    message_2 = (
        f'<pre>{html.escape(tb_string)}</pre>'
    )
    channel_id = config.TELEGRAM["channel"]["LOG"]["char_id"]
    try:
        if 'make sure that only one bot instance is running' in tb_string:
            Log.error("其他机器人在运行，请停止！")
            return
        context.bot.send_message(chat_id=channel_id, text=message_1, parse_mode=ParseMode.HTML)
        context.bot.send_message(chat_id=channel_id, text=message_2, parse_mode=ParseMode.HTML)
    except BadRequest as exc:
        if 'too long' in str(exc):
            message = (
                f'<b>处理函数时发生异常，traceback太长导致无法发送，但已写入日志</b> \n'
                f'<code>{html.escape(str(context.error))}</code>'
            )
            context.bot.send_message(chat_id=channel_id, text=message)
        else:
            raise exc
