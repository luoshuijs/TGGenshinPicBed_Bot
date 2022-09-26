import json
import os
import time
import traceback

from telegram import Update, ParseMode, ReplyKeyboardRemove
from telegram.error import BadRequest
from telegram.ext import CallbackContext

from config import config
from logger import Log

notice_chat_id = config.TELEGRAM["channel"]["LOG"]["char_id"]
current_dir = os.getcwd()
logs_dir = os.path.join(current_dir, "logs")
if not os.path.exists(logs_dir):
    os.mkdir(logs_dir)
report_dir = os.path.join(current_dir, "report")
if not os.path.exists(report_dir):
    os.mkdir(report_dir)


def error_handler(update: object, context: CallbackContext) -> None:
    """记录错误并发送消息通知开发人员。 logger the error and send a telegram message to notify the developer."""

    Log.error("处理函数时发生异常")

    if notice_chat_id is None:
        return

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)

    error_text = (
        f"-----Exception while handling an update-----\n"
        f"update = {json.dumps(update_str, indent=2, ensure_ascii=False)}\n"
        f"context.chat_data = {str(context.chat_data)}\n"
        f"context.user_data = {str(context.user_data)}\n"
        "\n"
        "-----Traceback info-----\n"
        f"{tb_string}"
    )
    file_name = f"error_{update.update_id if isinstance(update, Update) else int(time.time())}.txt"
    log_file = os.path.join(report_dir, file_name)
    try:
        with open(log_file, mode='w+', encoding='utf-8') as f:
            f.write(error_text)
    except Exception:
        Log.error("保存日记失败")
    try:
        if 'make sure that only one bot instance is running' in tb_string:
            Log.error("其他机器人在运行，请停止！")
            return
        if 'Message is not modified' in tb_string:
            Log.error("消息未修改")
            return
        context.bot.send_document(chat_id=notice_chat_id, document=open(log_file, "rb"),
                                  caption=f"Error: \"{context.error.__class__.__name__}\"")
    except BadRequest:
        Log.error("发送日记失败")
    except FileNotFoundError:
        Log.error("发送日记失败 文件不存在")
    effective_user = update.effective_user
    effective_message = update.effective_message
    try:
        if effective_message is not None:
            chat = effective_message.chat
            Log.info(f"尝试通知用户 {effective_user.full_name}[{effective_user.id}] "
                     f"在 {chat.full_name}[{chat.id}]"
                     f"的 update_id[{update.update_id}] 错误信息")
            text = "出错了呜呜呜 ~ 派蒙这边发生了点问题无法处理！"
            context.bot.send_message(effective_message.chat_id, text, reply_markup=ReplyKeyboardRemove(),
                                     parse_mode=ParseMode.HTML)
    except BadRequest:
        Log.error(f"发送 update_id[{update.update_id}] 错误信息失败 错误信息为")
