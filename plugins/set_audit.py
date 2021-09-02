from telegram import Update, InputMediaPhoto, ParseMode, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler
import telegram

from src.base.config import config
from src.base.utils.base import Utils
from src.base.utils.markdown import markdown_escape
from src.base.utils.artid import ExtractArtid
from src.base.model.artwork import AuditStatus, AuditType
from src.base.logger import Log
from src.production.pixiv import PixivService


class SetHandlerData:
    def __init__(self):
        self.art_id: int = -1
        self.channel_id: int = -1
        self.forward_from_message_id: int = -1
        self.forward_date: int = -1
        self.channel_id: int = -1
        self.operation: str = ""


class SetAuditHandler:
    QUERY, = -1000,
    ONE, TWO, THREE, FOUR = range(4)

    def __init__(self, pixiv: PixivService = None):
        self.utils = Utils(config)
        self.pixiv = pixiv

    def command_handler(self, update: Update, context: CallbackContext):
        user = update.effective_user
        Log.info("examine命令请求 user %s id %s" % (user["username"], user["id"]))
        if not self.utils.IfAdmin(user["id"]):
            update.message.reply_text("你不是BOT管理员，不能使用此命令！")
            return ConversationHandler.END
        SetAuditHandlerData = SetHandlerData()
        context.chat_data["SetAuditHandlerData"] = SetAuditHandlerData
        art_id: int = -1
        if update.message.reply_to_message is not None:
            for caption_entities in update.message.reply_to_message.caption_entities:
                if caption_entities.type == telegram.constants.MESSAGEENTITY_TEXT_LINK:
                    try:
                        art_id_str = ExtractArtid(caption_entities.url)
                        art_id = int(art_id_str)
                    except (IndexError, ValueError, TypeError):
                        pass
            if art_id != -1:
                SetAuditHandlerData.art_id = art_id
                reply_to_message = update.message.reply_to_message
                if reply_to_message.forward_from_chat is not None:
                    if reply_to_message.forward_from_chat.type == "channel":
                        SetAuditHandlerData.forward_date = reply_to_message.forward_date.timestamp()
                        SetAuditHandlerData.forward_from_message_id = reply_to_message.forward_from_message_id
                        SetAuditHandlerData.channel_id = reply_to_message.forward_from_chat.id
                return self.set_start(update, context)
            else:
                update.message.reply_text("回复的信息无连接信息，请重新回复")
                return ConversationHandler.END
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
        if SetAuditHandlerData.art_id == -1:
            try:
                art_id_str = ExtractArtid(update.message.text)
                art_id = int(art_id_str)
            except (IndexError, ValueError, TypeError):
                update.message.reply_text("获取作品信息失败，请检连接或者ID是否有误", reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
        else:
            art_id = SetAuditHandlerData.art_id
        Log.info("用户 %s 请求修改作品(%s)" % (user.username, art_id))
        artwork_data = self.pixiv.get_artwork_image_by_art_id(art_id)
        if artwork_data is None:
            update.message.reply_text(f"作品 {art_id} 不存在或出现未知错误", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        if SetAuditHandlerData.forward_from_message_id != -1:
            reply_keyboard = [['status', 'type'], ["退出"]]
            update.message.reply_text("获取作品信息成功，请选择你要修改的类型",
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return self.TWO
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
                update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
        except BadRequest as TError:
            update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
            Log.error("encounter error with image caption\n%s" % caption)
            Log.error(TError)
            return ConversationHandler.END
        SetAuditHandlerData.art_id = artwork_info.art_id
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
        try:
            art_id = SetAuditHandlerData.art_id
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
        if forward_from_message_id != -1:
            channel_id = SetAuditHandlerData.channel_id
            forward_date = SetAuditHandlerData.forward_date
            if update.message.date.timestamp() - forward_date < 48 * 60 * 60:
                # https://python-telegram-bot.readthedocs.io/en/stable/telegram.bot.html?highlight=delete_message#telegram.Bot.delete_message
                # A message can only be deleted if it was sent less than 48 hours ago.
                if info_type == "status" and update_data == AuditStatus.REJECT.value:
                    try:
                        context.bot.delete_message(channel_id, forward_from_message_id)
                    except BadRequest as err:
                        Log.error(err)
                        update.message.reply_text("删除失败，请检查是否授权管理员权限", reply_markup=ReplyKeyboardRemove())
                        return ConversationHandler.END
                    context.bot.send_message(update.message.chat_id, f"作品 {art_id} 已更新 {info_type} 为 {update_data}"
                                                                     f"并且已经从频道删除",
                                             reply_markup=ReplyKeyboardRemove())
            else:
                update.message.reply_text(f"作品 {art_id} 已更新 {info_type} 为 {update_data}"
                                          f"注意：推送时间已经超过48H，请手动删除", reply_markup=ReplyKeyboardRemove())
        else:
            update.message.reply_text(f"作品 {art_id} 已更新 {info_type} 为 {update_data}",
                                      reply_markup=ReplyKeyboardRemove())
        self.pixiv.set_art_audit_info(art_id, info_type, update_data)
        Log.info("用户 %s 请求修改作品(%s): [%s]" % (user.username, art_id, info_type))
        return ConversationHandler.END
