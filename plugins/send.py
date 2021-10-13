import uuid
from typing import Iterable, Optional

import telegram
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, ParseMode, InputMediaDocument, \
    Document, InputFile
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from logger import Log
from config import config
from model.artwork import ArtworkImage, ArtworkInfo, AuditType, AuditStatus
from utils.base import Utils
from utils.markdown import markdown_escape
from service import Service


class SendHandlerData:
    def __init__(self):
        self.channel_id: int = -1
        self.channel_name: str = ""
        self.url: str = ""
        self.artwork_info: Optional[ArtworkInfo] = None
        self.artwork_images: Optional[Iterable[ArtworkImage]] = None
        self.audit_type: AuditType = AuditType.SFW


class SendHandler:
    ONE, TWO, THREE, FOUR = range(4)

    def __init__(self, send_service: Service = None):
        self.utils = Utils(config)
        self.send_service = send_service

    def send_command(self, update: Update, context: CallbackContext) -> int:
        user = update.effective_user
        Log.info("send命令请求 user %s id %s" % (user["username"], user["id"]))
        if not self.utils.IfAdmin(user["id"]):
            update.message.reply_text("你不是BOT管理员，不能使用此命令！")
            return ConversationHandler.END
        send_handler_data = context.chat_data.get("send_handler_data")
        if send_handler_data is None:
            send_handler_data = SendHandlerData()
            context.chat_data["send_handler_data"] = send_handler_data
        else:
            send_handler_data.url = ""
        if update.message.caption_entities is not None:
            for caption_entities in update.message.caption_entities:
                if caption_entities.type == telegram.constants.MESSAGEENTITY_TEXT_LINK:
                    send_handler_data.url = caption_entities.url
        if update.message.reply_to_message is not None:
            for caption_entities in update.message.reply_to_message.caption_entities:
                if caption_entities.type == telegram.constants.MESSAGEENTITY_TEXT_LINK:
                    send_handler_data.url = caption_entities.url
        if send_handler_data.url != "":
            return self.get_info(update, context)
        message = "✿✿ヽ（°▽°）ノ✿ 你好！ %s ，欢迎 \n" \
                  "当前直投只支持Twitter和MihoyoBBS \n" \
                  "只需复制URL回复即可 \n" \
                  "退出投稿只需回复退出" % (user["username"])
        reply_keyboard = [['退出']]
        update.message.reply_text(text=message,
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.ONE

    def get_info(self, update: Update, context: CallbackContext) -> int:
        send_handler_data: SendHandlerData = context.chat_data.get("send_handler_data")
        if update.message.text == "退出":
            update.message.reply_text(text="退出投稿", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        if update.message.text is None:
            update.message.reply_text(text="回复错误", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        if send_handler_data.url == "":
            artwork_data = self.send_service.get_info_by_url(update.message.text)
        else:
            artwork_data = self.send_service.get_info_by_url(send_handler_data.url)
        if artwork_data is None:
            update.message.reply_text("已经存在数据库或者频道，退出投稿", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        artwork_info, images = artwork_data
        send_handler_data.artwork_info = artwork_info
        send_handler_data.artwork_images = images
        caption = "Title %s   \n" \
                  "%s   \n" \
                  "Tags %s   \n" \
                  "From [%s](%s)" % (
                      markdown_escape(artwork_info.title),
                      artwork_info.GetStringStat(),
                      markdown_escape(artwork_info.GetStringTags(filter_character_tags=True)),
                      artwork_info.site_name,
                      artwork_info.origin_url
                  )
        try:
            if len(images) > 1:
                media = [InputMediaPhoto(media=img_info.data) for img_info in images]
                media = media[:10]
                media[0] = InputMediaPhoto(media=images[0].data, caption=caption,
                                           parse_mode=ParseMode.MARKDOWN_V2)
                update.message.reply_media_group(media, timeout=30)
            elif len(images) == 1:
                image = images[0]
                if image.format == "gif":
                    update.message.reply_document(document=image.data,
                                                  filename=f"{artwork_info.post_id}.{image.format}",
                                                  caption=caption,
                                                  timeout=30,
                                                  parse_mode=ParseMode.MARKDOWN_V2)
                else:
                    update.message.reply_photo(photo=image.data,
                                               caption=caption,
                                               timeout=30,
                                               parse_mode=ParseMode.MARKDOWN_V2)
            else:
                update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())  # excuse?
                return ConversationHandler.END
        except (BadRequest, TypeError) as TError:
            update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
            Log.error("encounter error with image caption\n%s" % caption)
            Log.error(TError)
            return ConversationHandler.END
        reply_keyboard = [['SFW', 'NSFW'], ['R18', '退出']]
        message = "请选择你推送到的频道"
        update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.TWO

    def get_channel(self, update: Update, context: CallbackContext) -> int:
        send_handler_data: SendHandlerData = context.chat_data.get("send_handler_data")
        if update.message.text == "退出":
            update.message.reply_text(text="退出任务", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        try:
            send_handler_data.audit_type = audit_type = AuditType(update.message.text)
            channel_name = config.TELEGRAM["channel"][audit_type.value]["name"]
            channel_id = config.TELEGRAM["channel"][audit_type.value]["char_id"]
            send_handler_data.channel_id = channel_id
            send_handler_data.channel_name = channel_name
        except KeyError:
            update.message.reply_text(text="发生错误，退出任务", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        update.message.reply_text("你选择的频道名称为 %s 类型为 %s" % (channel_name, audit_type.value))
        reply_keyboard = [['确认', '取消']]
        message = "请确认推送的频道和作品的信息"
        update.message.reply_text(
            message,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return self.THREE

    def send_message(self, update: Update, context: CallbackContext) -> int:
        send_handler_data: SendHandlerData = context.chat_data.get("send_handler_data")
        update.message.reply_text("正在推送", reply_markup=ReplyKeyboardRemove())
        channel_id = send_handler_data.channel_id
        if update.message.text == "取消":
            update.message.reply_text(text="退出任务", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        artwork_info: ArtworkInfo = send_handler_data.artwork_info
        images: Iterable[ArtworkImage] = send_handler_data.artwork_images
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
                media = [InputMediaPhoto(media=img_info.data) for img_info in images]
                media = media[:10]
                media[0] = InputMediaPhoto(media=images[0].data, caption=caption,
                                           parse_mode=ParseMode.MARKDOWN_V2)
                context.bot.send_media_group(channel_id, media=media, timeout=30)
            elif len(images) == 1:
                image = images[0]
                if image.format == "gif":
                    context.bot.send_document(channel_id, document=image.data,
                                              filename=f"{artwork_info.post_id}.gif",
                                              caption=caption,
                                              timeout=30,
                                              parse_mode=ParseMode.MARKDOWN_V2)
                else:
                    context.bot.send_photo(channel_id, photo=image.data,
                                           caption=caption,
                                           timeout=30,
                                           parse_mode=ParseMode.MARKDOWN_V2)
            else:
                update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
        except BadRequest as TError:
            update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
            Log.error("encounter error with image caption\n%s" % caption)
            Log.error(TError)
            return ConversationHandler.END
        update.message.reply_text("推送完成", reply_markup=ReplyKeyboardRemove())
        self.send_service.save_artwork_info(artwork_info, send_handler_data.audit_type, AuditStatus.PUSH)
        return ConversationHandler.END
