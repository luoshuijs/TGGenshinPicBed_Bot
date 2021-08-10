from telegram import Update, InputMediaPhoto, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

import re
import ujson
from src.base.utils.markdown import markdown_escape
from src.base.utils.artid import ExtractArtid
from src.base.model.artwork import AuditStatus, AuditType, ArtworkInfo
from src.base.logger import Log
from src.production.pixiv import PixivService


class SetAuditHandler:
    QUERY, = range(1)

    def __init__(self, pixiv: PixivService = None):
        self.pixiv = pixiv

    def command_handler(self, update: Update, context: CallbackContext):
        user = update.effective_user
        Log.info("set命令请求 user %s id %s" % (user.username, user.id))
        try:
            operation = context.args[0]
            art_id = int(ExtractArtid(context.args[1]))
            Log.info("用户 %s 请求修改作品(%s): [%s]" % (user.username, art_id, operation))
            artwork_data = self.pixiv.get_artwork_image_by_art_id(art_id)
            if artwork_data is None:
                update.message.reply_text(f"作品 {art_id} 不存在或出现未知错误")
                return ConversationHandler.END
            if operation not in ["status", "type"]:
                update.message.reply_text("```\n"
                                          "Usage: /set status <art_id>\n\n"
                                          "       /set type <art_id>```",
                                          parse_mode=ParseMode.MARKDOWN_V2)
                return ConversationHandler.END
        except (IndexError, ValueError):
            update.message.reply_text("```\n"
                                      "Usage: /set status <art_id>\n"
                                      "       /set type <art_id>```",
                                      parse_mode=ParseMode.MARKDOWN_V2)
            return ConversationHandler.END
        artwork_info, images = artwork_data
        url = "https://www.pixiv.net/artworks/%s" % art_id
        caption = "Type: %s   \n" \
                  "Status: %s   \n" \
                  "Title %s   \n" \
                  "Views %s Likes %s Loves %s   \n" \
                  "Tags %s   \n" \
                  "From [Pixiv](%s)" % (
                      markdown_escape(artwork_info.audit_info.audit_type.value),
                      markdown_escape(artwork_info.audit_info.audit_status.name),
                      markdown_escape(artwork_info.title),
                      artwork_info.view_count,
                      artwork_info.like_count,
                      artwork_info.love_count,
                      markdown_escape(artwork_info.tags),
                      url
                  )
        try:
            if len(images) > 1:
                media = [InputMediaPhoto(media=img_info.data) for img_info in images]
                media = media[:10]
                media[0] = InputMediaPhoto(media=images[0].data, caption=caption,
                                           parse_mode=ParseMode.MARKDOWN_V2)
                update.message.reply_media_group(media, timeout=30)
            elif len(images) == 1:
                photo = images[0].data
                update.message.reply_photo(photo=photo,
                                           caption=caption,
                                           timeout=30,
                                           parse_mode=ParseMode.MARKDOWN_V2)
            else:
                Log.error("图片%s获取失败" % art_id)
                update.message.reply_text("图片获取错误，找开发者背锅吧~")  # excuse?
                return ConversationHandler.END
        except BadRequest as TError:
            update.message.reply_text("图片获取错误，找开发者背锅吧~")
            Log.error("encounter error with image caption\n%s" % caption)
            Log.error(TError)
            return ConversationHandler.END
        art_id = artwork_info.art_id
        audit_status = artwork_info.audit_info.audit_status
        audit_type = artwork_info.audit_info.audit_type
        if operation == "status":
            keyboard = [
                [
                    InlineKeyboardButton("PASS", callback_data=ujson.dumps([art_id, "status", AuditStatus.PASS.value])),
                    InlineKeyboardButton("REJECT",
                                         callback_data=ujson.dumps([art_id, "status", AuditStatus.REJECT.value])),
                    InlineKeyboardButton("PUSH", callback_data=ujson.dumps([art_id, "status", AuditStatus.PUSH.value])),
                    InlineKeyboardButton("Cancel", callback_data="Cancel"),
                ]
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton("SFW", callback_data=ujson.dumps([art_id, "type", AuditType.SFW.value])),
                    InlineKeyboardButton("NSFW", callback_data=ujson.dumps([art_id, "type", AuditType.NSFW.value])),
                    InlineKeyboardButton("R18", callback_data=ujson.dumps([art_id, "type", AuditType.R18.value])),
                    InlineKeyboardButton("Cancel", callback_data="Cancel"),
                ]
            ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(f"作品 {art_id} 修改 {operation}", reply_markup=reply_markup)
        return self.QUERY

    def set_audit_info(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()
        data = query.data
        if data == "Cancel":
            query.edit_message_text(f"作品取消更新")
            return ConversationHandler.END
        try:
            art_id, info_type, update_data = ujson.loads(data)
            self.pixiv.set_art_audit_info(art_id, info_type, update_data)
            query.edit_message_text(f"作品 {art_id} 已更新 {info_type} 为 {update_data}")
        except Exception as TError:
            Log.error(TError)
            query.edit_message_text(f"发生未知错误, 联系开发者 - "
                                    "(art_id {art_id}, info_type {info_type}, "
                                    "update_data {update_data})")
        return ConversationHandler.END
