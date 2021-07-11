from telegram import Update, InputMediaPhoto, ParseMode, InlineKeyboardButton, \
    InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from src.base.config import config
from src.base.utils import Utils
from src.base.logger import Log
from src.production.markdown import markdown_escape
from src.production.pixiv.pixiv import pixiv

import time

utils = Utils(config)

ONE, TWO, THREE, FOUR = range(4)

def push(update: Update, _: CallbackContext) -> int:
    user = update.effective_user
    Log.info("push命令请求 user %s id %s" % (user["username"], user["id"]))
    if not utils.IfAdmin(user["id"]):
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
    return ONE


def PushInfo(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == "退出":
        query.edit_message_text('退出推送')
        return ConversationHandler.END
    keyboard = [
        [
            InlineKeyboardButton("OK", callback_data=str(TWO)),
            InlineKeyboardButton("退出", callback_data=str(THREE)),
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
    return TWO


def StartPush(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == "退出":
        query.edit_message_text('退出推送')
        return ConversationHandler.END
    query.edit_message_text(text="正在初始化")
    audit_type = context.chat_data.get("audit_type", None)
    pixiv_ = None
    sendReq = None
    if audit_type == "SFW":
        pixiv_ = pixiv.sfw
    elif audit_type == "NSFW":
        pixiv_ = pixiv.nsfw
    elif audit_type == "R18":
        pixiv_ = pixiv.r18
    else:
        raise ValueError("unknown audit_type %s" % audit_type)
    Req = pixiv_.push_v1()
    message = "无推送任务，点击确认退出任务"
    if Req.status:
        remaining = Req.data["count"]
        while remaining > 0:
            char_id = context.chat_data.get("push_char_id", 0)
            if char_id == 0:
                query.edit_message_text(text="推送发生错误")
                return ConversationHandler.END
            with pixiv_.nextpush_v1() as Req:
                remaining = Req.data["remaining"]
                query.edit_message_text(text="还剩下%s张图片正在排队..." % remaining)
                url = "https://www.pixiv.net/artworks/%s" % Req.data["information"]["illusts_id"]
                caption = "Title %s   \n" \
                          "Tags %s   \n" \
                          "From [Pixiv](%s)" % (
                              markdown_escape(Req.data["information"]["title"]),
                              markdown_escape(Req.data["information"]["tags"]),
                              url
                          )
                artwork = Req.data["img"]
                try:
                    if artwork.count > 1:
                        media = [InputMediaPhoto(artwork.image_list[0], caption=caption, parse_mode=ParseMode.MARKDOWN_V2)]
                        for _, img_data in enumerate(artwork.image_list[1:]):
                            media.append(InputMediaPhoto(img_data, parse_mode=ParseMode.MARKDOWN_V2))
                        media = media[:9]
                        sendReq = context.bot.send_media_group(char_id, media)
                        time.sleep(len(media))
                    elif artwork.count == 1:
                        photo = artwork.image_list[0]
                        sendReq = context.bot.send_photo(char_id, photo, caption=caption,
                                                         parse_mode=ParseMode.MARKDOWN_V2)
                        time.sleep(1)
                except BadRequest as TError:
                    Log.error("encountered error with image caption\n%s" % caption)
                    Log.error(TError)
                    update.message.reply_text("图片发送出错")
                    return ConversationHandler.END
                if audit_type == "NSFW" and not sendReq is None:
                    channel_name = config.TELEGRAM["channel"]["NSFW"]["name"]
                    channel_id = config.TELEGRAM["channel"]["SFW"]["char_id"]
                    if isinstance(sendReq, list):
                        message_id = sendReq[0].message_id
                    else:
                        message_id = sendReq.message_id
                    url = "https://t.me/%s/%s" % (channel_name, message_id)
                    reply_keyboard = [
                        [
                            InlineKeyboardButton("点击查看/Click it to view", url=url),
                        ]
                    ]
                    text = " **NSFW警告/NSFW warning**   \n" \
                           "      \n" \
                           "%s" % caption
                    context.bot.send_message(channel_id, text=text, reply_markup=InlineKeyboardMarkup(reply_keyboard),
                                             parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
                if remaining == 0:
                    message = "推送完毕，点击确认退出任务"
    keyboard = [
        [
            InlineKeyboardButton("确认", callback_data=str(THREE)),
        ]
    ]
    query.edit_message_text(text=message, reply_markup=InlineKeyboardMarkup(keyboard))
    return THREE


def EndPush(update: Update, _: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="推送完成")
    return ConversationHandler.END