from telegram import Update, InputMediaPhoto, ParseMode, InlineKeyboardButton, \
    InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from src.base.config import config
from src.base.utils import Utils
from src.base.logger import Log
from src.production.markdown import markdown_escape
from src.production.pixiv.service import PixivService
from src.model.artwork import AuditType

import time


class PushHandler:
    ONE, TWO, THREE = range(3)

    def __init__(self, pixiv: PixivService = None):
        self.utils = Utils(config)
        self.pixiv = pixiv

    def command_handler(self, update: Update, _: CallbackContext) -> int:
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
        return self.ONE

    def setup_handler(self, update: Update, context: CallbackContext) -> int:
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
        channel_name = config.TELEGRAM["channel"][query.data]["name"]
        channel_id = config.TELEGRAM["channel"][query.data]["char_id"]
        message = "嗯，我看见了。\n" \
                  "频道名称 %s  推送类型 %s。\n" \
                  "请点击OK继续。" % (channel_name, query.data)
        context.chat_data["push_char_id"] = channel_id
        context.chat_data["audit_type"] = query.data
        query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        return self.TWO

    def start_handler(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        query.answer()
        if query.data == "退出":
            query.edit_message_text('退出推送')
            return ConversationHandler.END
        query.edit_message_text(text="正在初始化")
        audit_type = AuditType(context.chat_data.get("audit_type", None))
        sendReq = None
        remaining = self.pixiv.push_start(audit_type)
        message = "无推送任务，点击确认退出任务"
        while remaining > 0:
            char_id = context.chat_data.get("push_char_id", 0)
            if char_id == 0:
                query.edit_message_text(text="推送发生错误")
                return ConversationHandler.END
            result = self.pixiv.push_next(audit_type)
            if result is None:
                message = "推送完毕，点击确认退出任务"
                break
            artwork_info, images, remaining = result
            with self.pixiv.push_manager(artwork_info):
                query.edit_message_text(text="还剩下%s张图片正在排队..." % remaining)
                url = "https://www.pixiv.net/artworks/%s" % artwork_info.art_id
                caption = "Title %s   \n" \
                          "Tags %s   \n" \
                          "From [Pixiv](%s)" % (
                              markdown_escape(artwork_info.title),
                              markdown_escape(artwork_info.tags),
                              url
                          )
                try:
                    if len(images) > 1:
                        media = [InputMediaPhoto(images[0].data, caption=caption, parse_mode=ParseMode.MARKDOWN_V2)]
                        for _, img in enumerate(images[1:10]):
                            media.append(InputMediaPhoto(img.data, parse_mode=ParseMode.MARKDOWN_V2))
                        sendReq = context.bot.send_media_group(char_id, media)
                        time.sleep(len(media) * 2)
                    elif len(images) == 1:
                        photo = images[0].data
                        sendReq = context.bot.send_photo(char_id, photo, caption=caption,
                                                         parse_mode=ParseMode.MARKDOWN_V2)
                        time.sleep(1)
                except BadRequest as TError:
                    Log.error("encountered error with image caption\n%s" % caption)
                    Log.error(TError)
                    update.message.reply_text("图片发送出错")
                    return ConversationHandler.END
                if audit_type.name == "NSFW" or audit_type.name == "R18":
                    if isinstance(sendReq, list):
                        message_id = sendReq[0].message_id
                    else:
                        message_id = sendReq.message_id
                    if audit_type.name == "NSFW":
                        channel_name = config.TELEGRAM["channel"]["NSFW"]["name"]
                        channel_id = config.TELEGRAM["channel"]["SFW"]["char_id"]
                    elif audit_type.name == "R18":
                        channel_name = config.TELEGRAM["channel"]["R18"]["name"]
                        channel_id = config.TELEGRAM["channel"]["NSFW"]["char_id"]
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
