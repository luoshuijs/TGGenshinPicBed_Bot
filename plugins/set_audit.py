from typing import Optional, Iterable

import telegram
from telegram import Update, InputMediaPhoto, ParseMode, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler
from telegram.utils.helpers import escape_markdown

from config import config
from model.artwork import ArtworkInfo, ArtworkImage
from utils.base import Utils
from model.artwork import AuditStatus, AuditType
from logger import Log
from service import AuditService, SiteService


class SetHandlerData:
    def __init__(self):
        self.channel_id: int = -1
        self.forward_from_message_id: int = -1
        self.forward_date: int = -1
        self.operation: str = ""
        self.url: str = ""
        self.artwork_info: Optional[ArtworkInfo] = None
        self.artwork_images: Optional[Iterable[ArtworkImage]] = None


class SetAuditHandler:
    ONE, TWO, THREE, FOUR = range(10700, 10704)

    def __init__(self, site_service: SiteService = None, audit_service: AuditService = None):
        self.utils = Utils(config)
        self.site_service = site_service
        self.audit_service = audit_service

    def command_handler(self, update: Update, context: CallbackContext):
        user = update.effective_user
        Log.info("examine命令请求 user %s id %s" % (user["username"], user["id"]))
        if not self.utils.IfAdmin(user["id"]):
            update.message.reply_text("你不是BOT管理员，不能使用此命令！")
            return ConversationHandler.END
        SetAuditHandlerData = SetHandlerData()
        context.chat_data["SetAuditHandlerData"] = SetAuditHandlerData
        if update.message.caption_entities is not None:
            for caption_entities in update.message.caption_entities:
                if caption_entities.type == telegram.constants.MESSAGEENTITY_TEXT_LINK:
                    SetAuditHandlerData.url = caption_entities.url
            if SetAuditHandlerData.url != "":
                return self.set_start(update, context)
        if update.message.reply_to_message is not None:
            for caption_entities in update.message.reply_to_message.caption_entities:
                if caption_entities.type == telegram.constants.MESSAGEENTITY_TEXT_LINK:
                    SetAuditHandlerData.url = caption_entities.url
            reply_to_message = update.message.reply_to_message
            if reply_to_message.forward_from_chat is not None:
                if reply_to_message.forward_from_chat.type == "channel":
                    SetAuditHandlerData.forward_date = reply_to_message.forward_date.timestamp()
                    SetAuditHandlerData.forward_from_message_id = reply_to_message.forward_from_message_id
                    SetAuditHandlerData.channel_id = reply_to_message.forward_from_chat.id
            return self.set_start(update, context)
        Log.info("set命令请求 user %s id %s" % (user.username, user.id))
        if not self.utils.IfAdmin(user["id"]):
            update.message.reply_text("你不是BOT管理员，不能使用此命令！")
            return ConversationHandler.END
        message = "✿✿ヽ（°▽°）ノ✿ 你好！ %s  \n" \
                  "重新设置审核状态复制URL回复即可 \n" \
                  "需要退出只需回复退出" % (user["username"])
        reply_keyboard = [["退出"]]
        update.message.reply_text(text=message,
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.ONE

    def set_start(self, update: Update, context: CallbackContext):
        SetAuditHandlerData: SetHandlerData = context.chat_data["SetAuditHandlerData"]
        user = update.effective_user
        if update.message.text == "退出":
            update.message.reply_text(text="退出任务", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        update.message.reply_text("正在获取作品信息", reply_markup=ReplyKeyboardRemove())
        if SetAuditHandlerData.url == "":
            artwork_data = self.site_service.get_info_by_url(update.message.text)
        else:
            artwork_data = self.site_service.get_info_by_url(SetAuditHandlerData.url)
        if artwork_data.is_error:
            update.message.reply_text("获取作品信息失败，请检连接或者ID是否有误", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        artwork_info = SetAuditHandlerData.artwork_info = artwork_data.artwork_info
        images = SetAuditHandlerData.artwork_images = artwork_data.artwork_image
        audit_info = self.audit_service.get_audit_info(artwork_info)
        if audit_info.site is None:
            update.message.reply_text("该作品未在审核数据库，退出任务", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        Log.info("用户 %s 请求修改作品(%s)" % (user.username, artwork_info.artwork_id))
        caption = "Type: %s   \n" \
                  "Status: %s   \n" \
                  "Site: %s   \n" \
                  "Title %s   \n" \
                  "%s \n" \
                  "Tags %s   \n" \
                  "From [%s](%s)" % (
                      audit_info.type.name,
                      audit_info.status.name,
                      audit_info.site,
                      escape_markdown(artwork_info.title.replace('\\', '\\\\'), version=2),
                      artwork_info.GetStringStat(),
                      escape_markdown(artwork_info.GetStringTags(filter_character_tags=True), version=2),
                      artwork_info.site_name,
                      artwork_info.origin_url
                  )
        if "/set" in update.message.text:
            reply_keyboard = [['status', 'type'], ["退出"]]
            update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN_V2,
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            update.message.reply_text("获取作品信息成功，请选择你要修改的类型",
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return self.TWO
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

                    update.message.reply_animation(animation=image.data,
                                                   caption=caption,
                                                   timeout=30,
                                                   parse_mode=ParseMode.MARKDOWN_V2)
                else:
                    update.message.reply_photo(photo=image.data,
                                               caption=caption,
                                               timeout=30,
                                               parse_mode=ParseMode.MARKDOWN_V2)
            else:
                Log.error("图片%s获取失败" % artwork_info.artwork_id)
                update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
        except BadRequest as TError:
            update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
            Log.error("encounter error with image caption\n%s" % caption)
            Log.error(TError)
            return ConversationHandler.END
        SetAuditHandlerData.art_id = artwork_info.artwork_id
        reply_keyboard = [['status', 'type'], ["退出"]]
        update.message.reply_text("请选择你要修改的类型",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.TWO

    def set_operation(self, update: Update, context: CallbackContext):
        SetAuditHandlerData: SetHandlerData = context.chat_data["SetAuditHandlerData"]
        if update.message.text == "退出":
            update.message.reply_text(text="退出任务", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        elif update.message.text == "status":
            reply_keyboard = [
                ['通过(1)', '撤销(2)'],
                ['已投稿(3)'],
                ["退出"]]
        elif update.message.text == "type":
            reply_keyboard = [
                ['SFW', 'NSFW'],
                ['R18'],
                ["退出"]]
        else:
            update.message.reply_text("命令错误", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        SetAuditHandlerData.operation = update.message.text
        update.message.reply_text("请选择你要修改的数据",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.THREE

    def set_audit_info(self, update: Update, context: CallbackContext):
        SetAuditHandlerData: SetHandlerData = context.chat_data["SetAuditHandlerData"]
        user = update.effective_user
        if update.message.text == "退出":
            update.message.reply_text(text="退出任务", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        post_id = SetAuditHandlerData.artwork_info.artwork_id
        try:
            info_type = SetAuditHandlerData.operation
            if info_type == "status":
                if update.message.text == "通过(1)":
                    update_data = AuditStatus.PASS.value
                elif update.message.text == "撤销(2)":
                    update_data = AuditStatus.REJECT.value
                elif update.message.text == "已投稿(3)":
                    update_data = AuditStatus.PUSH.value
                else:
                    update.message.reply_text("命令错误", reply_markup=ReplyKeyboardRemove())
                    return ConversationHandler.END
            elif info_type == "type":
                if update.message.text == "SFW":
                    update_data = AuditType.SFW.value
                elif update.message.text == "NSFW":
                    update_data = AuditType.NSFW.value
                elif update.message.text == "R18":
                    update_data = AuditType.R18.value
                else:
                    update.message.reply_text("命令错误", reply_markup=ReplyKeyboardRemove())
                    return ConversationHandler.END
            else:
                update.message.reply_text("命令错误", reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
        except Exception as err:
            Log.error(err)
            update.message.reply_text("发生未知错误, 联系开发者", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        forward_from_message_id = SetAuditHandlerData.forward_from_message_id
        if info_type == "status" and update_data == AuditStatus.REJECT.value:
            if forward_from_message_id != -1:
                channel_id = SetAuditHandlerData.channel_id
                forward_date = SetAuditHandlerData.forward_date
                if update.message.date.timestamp() - forward_date < 48 * 60 * 60:
                    # A message can only be deleted if it was sent less than 48 hours ago.
                    try:
                        context.bot.delete_message(channel_id, forward_from_message_id)
                    except BadRequest as err:
                        Log.error(err)
                        update.message.reply_text("删除失败，请检查是否授权管理员权限", reply_markup=ReplyKeyboardRemove())
                        return ConversationHandler.END
                    context.bot.send_message(update.message.chat_id, f"作品 {post_id} 已更新 {info_type} 为 {update_data}"
                                                                     f"并且已经从频道删除",
                                             reply_markup=ReplyKeyboardRemove())
                else:
                    update.message.reply_text(f"作品 {post_id} 已更新 {info_type} 为 {update_data}"
                                              f"注意：推送时间已经超过48H，请手动删除", reply_markup=ReplyKeyboardRemove())
            else:
                update.message.reply_text(f"作品 {post_id} 已更新 {info_type} 为 {update_data}",
                                          reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text(f"作品 {post_id} 已更新 {info_type} 为 {update_data}",
                                      reply_markup=ReplyKeyboardRemove())
        self.audit_service.set_art_audit_info(SetAuditHandlerData.artwork_info, info_type, update_data)
        Log.info("用户 %s 请求修改作品(%s): [%s]" % (user.username, post_id, info_type))
        return ConversationHandler.END
