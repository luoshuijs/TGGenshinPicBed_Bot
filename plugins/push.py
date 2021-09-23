from typing import Optional

from telegram import Update, InputMediaPhoto, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler
import time
from src.base.config import config
from src.base.utils.base import Utils
from src.base.logger import Log
from src.base.utils.markdown import markdown_escape
from src.base.model.artwork import AuditType
from src.production.service import Service


class PushHandlerData:
    def __init__(self):
        self.audit_type: Optional[AuditType] = None
        self.channel_id: int = 0
        self.channel_name: str = ""


class PushHandler:
    ONE, TWO, THREE = range(3)

    def __init__(self, service: Service = None):
        self.utils = Utils(config)
        self.service = service

    def command_handler(self, update: Update, context: CallbackContext) -> int:
        user = update.effective_user
        Log.info("push命令请求 user %s id %s" % (user["username"], user["id"]))
        if not self.utils.IfAdmin(user["id"]):
            update.message.reply_text("你不是BOT管理员，不能使用此命令！")
            return ConversationHandler.END
        message = "✿✿ヽ（°▽°）ノ✿ 你好！ %s ，请选择你的推送的类型" % (user["username"])
        keyboard = [
            [
                InlineKeyboardButton("SFW", callback_data="SFW"),
                InlineKeyboardButton("NSFW", callback_data="NSFW"),
                InlineKeyboardButton("R18", callback_data="R18"),
                InlineKeyboardButton("退出", callback_data="退出")
            ]
        ]
        update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        push_handler_data = PushHandlerData()
        context.chat_data["push_handler_data"] = push_handler_data
        return self.ONE

    def setup_handler(self, update: Update, context: CallbackContext) -> int:
        push_handler_data: PushHandlerData = context.chat_data["push_handler_data"]
        query = update.callback_query
        query.answer()
        if query.data == "退出":
            query.edit_message_text('退出推送')
            return ConversationHandler.END
        keyboard = [
            [
                InlineKeyboardButton("OK", callback_data="OK"),
                InlineKeyboardButton("退出", callback_data="退出"),
            ]
        ]
        push_handler_data.channel_name = config.TELEGRAM["channel"][query.data]["name"]
        push_handler_data.channel_id = config.TELEGRAM["channel"][query.data]["char_id"]
        message = "嗯，我看见了。\n" \
                  "频道名称 %s  推送类型 %s。\n" \
                  "请点击OK继续。" % (push_handler_data.channel_name, query.data)
        push_handler_data.audit_type = AuditType(query.data)
        query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        return self.TWO

    def start_handler(self, update: Update, context: CallbackContext) -> int:
        push_handler_data: PushHandlerData = context.chat_data["push_handler_data"]
        query = update.callback_query
        query.answer()
        if query.data == "退出":
            query.edit_message_text('退出推送')
            return ConversationHandler.END
        query.edit_message_text(text="正在初始化")
        audit_type = push_handler_data.audit_type
        sendReq = None
        remaining = self.service.audit.push_start(audit_type)
        message = "无推送任务，点击确认退出任务"
        while remaining > 0:
            result = self.service.audit.push_next(audit_type)
            if result is None:
                message = "推送完毕，点击确认退出任务"
                break
            artwork_info, images, remaining = result
            with self.service.audit.push_manager(artwork_info):
                query.edit_message_text(text="还剩下%s张图片正在排队..." % remaining)
                caption = "Title %s   \n" \
                          "Tags %s   \n" \
                          "From [%s](%s)" % (
                              markdown_escape(artwork_info.title),
                              markdown_escape(artwork_info.GetStringTags(filter_character_tags=True)),
                              artwork_info.site_name,
                              artwork_info.origin_url
                          )
                try:
                    if len(images) > 1:
                        media = [InputMediaPhoto(images[0].data, caption=caption, parse_mode=ParseMode.MARKDOWN_V2)]
                        for _, img in enumerate(images[1:10]):
                            media.append(InputMediaPhoto(img.data, parse_mode=ParseMode.MARKDOWN_V2))
                        sendReq = context.bot.send_media_group(push_handler_data.channel_id, media)
                        time.sleep(len(media) * 2)
                    elif len(images) == 1:
                        photo = images[0].data
                        sendReq = context.bot.send_photo(push_handler_data.channel_id, photo, caption=caption,
                                                         parse_mode=ParseMode.MARKDOWN_V2)
                        time.sleep(2)
                except BadRequest as TError:
                    Log.error("encountered error with image caption\n%s" % caption)
                    Log.error(TError)
                    update.message.reply_text("图片发送出错")
                    return ConversationHandler.END
                if audit_type == AuditType.NSFW:
                    if isinstance(sendReq, list):
                        message_id = sendReq[0].message_id
                    else:
                        message_id = sendReq.message_id
                    if audit_type.name == AuditType.NSFW:
                        channel_name = config.TELEGRAM["channel"]["NSFW"]["name"]
                        channel_id = config.TELEGRAM["channel"]["SFW"]["char_id"]
                    url = "https://t.me/%s/%s" % (channel_name, message_id)
                    reply_keyboard = [
                        [
                            InlineKeyboardButton("点击查看/Click it to view", url=url),
                        ]
                    ]
                    text = " **%s警告/%s warning**   \n" \
                           "      \n" \
                           "%s" % (audit_type.name, audit_type.name, caption)
                    context.bot.send_message(channel_id, text=text, reply_markup=InlineKeyboardMarkup(reply_keyboard),
                                             parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
                    time.sleep(1)
        keyboard = [
            [
                InlineKeyboardButton("确认", callback_data=str(self.THREE)),
            ]
        ]
        query.edit_message_text(text=message, reply_markup=InlineKeyboardMarkup(keyboard))
        return self.THREE

    def end_handler(self, update: Update, _: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        query.edit_message_text(text="推送完成")
        return ConversationHandler.END
