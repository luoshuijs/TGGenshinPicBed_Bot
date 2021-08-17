from telegram import Update, InputMediaPhoto, ParseMode, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from src.base.config import config
from src.base.utils.base import Utils
from src.base.utils.markdown import markdown_escape
from src.base.utils.artid import ExtractArtid
from src.base.model.artwork import AuditStatus, AuditType, ArtworkInfo
from src.base.logger import Log
from src.production.pixiv import PixivService


class SetAuditHandler:
    QUERY, = -1000,
    ONE, TWO, THREE, FOUR = range(4)

    def __init__(self, pixiv: PixivService = None):
        self.utils = Utils(config)
        self.pixiv = pixiv

    def command_handler(self, update: Update, context: CallbackContext):
        user = update.effective_user
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
        user = update.effective_user
        # update.message.reply_text("正在获取作品信息", reply_markup=ReplyKeyboardRemove())
        try:
            art_id_str = ExtractArtid(update.message.text)
            art_id = int(art_id_str)
        except (IndexError, ValueError, TypeError):
            update.message.reply_text("获取作品信息失败，请检连接或者ID是否有误", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        Log.info("用户 %s 请求修改作品(%s)" % (user.username, art_id))
        try:
            artwork_data = self.pixiv.get_artwork_image_by_art_id(art_id)
            if artwork_data is None:
                update.message.reply_text(f"作品 {art_id} 不存在或出现未知错误", reply_markup=ReplyKeyboardRemove())
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
                update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
        except BadRequest as TError:
            update.message.reply_text("图片获取错误，找开发者背锅吧~", reply_markup=ReplyKeyboardRemove())
            Log.error("encounter error with image caption\n%s" % caption)
            Log.error(TError)
            return ConversationHandler.END
        art_id = artwork_info.art_id
        context.chat_data["SetCommand"] = {}
        context.chat_data["SetCommand"]["art_id"] = art_id
        reply_keyboard = [['status', 'type'], ["退出"]]
        update.message.reply_text("请选择你要修改的类型",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.TWO

    def set_operation(self, update: Update, context: CallbackContext):
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
        context.chat_data["SetCommand"]["operation"] = update.message.text
        update.message.reply_text("请选择你要修改的数据",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.THREE

    def set_audit_info(self, update: Update, context: CallbackContext):
        user = update.effective_user
        if update.message.text == "退出":
            update.message.reply_text(text="退出任务", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        try:
            art_id = context.chat_data["SetCommand"]["art_id"]
            info_type = context.chat_data["SetCommand"]["operation"]
            update_data = -1
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
            self.pixiv.set_art_audit_info(art_id, info_type, update_data)
            update.message.reply_text(f"作品 {art_id} 已更新 {info_type} 为 {update_data}",
                                      reply_markup=ReplyKeyboardRemove())
        except Exception as TError:
            Log.error(TError)
            update.message.reply_text(f"发生未知错误, 联系开发者 - "
                                      f"(art_id {art_id}, info_type {info_type}, "
                                      f"update_data {update_data})")
        Log.info("用户 %s 请求修改作品(%s): [%s]" % (user.username, art_id, info_type))
        return ConversationHandler.END
