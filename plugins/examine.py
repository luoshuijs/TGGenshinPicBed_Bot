from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from src.base.config import config

from src.base.utils.base import Utils
from src.base.logger import Log
from src.base.utils.markdown import markdown_escape
from src.production.pixiv.service import PixivService
from src.base.model.artwork import AuditType


class ExamineHandler:
    EXAMINE, EXAMINE_START, EXAMINE_RESULT, EXAMINE_REASON = range(4)

    def __init__(self, pixiv: PixivService = None):
        self.utils = Utils(config)
        self.pixiv = pixiv

    def command_handler(self, update: Update, _: CallbackContext) -> int:
        user = update.effective_user
        Log.info("examine命令请求 user %s id %s" % (user["username"], user["id"]))
        if not self.utils.IfAdmin(user["id"]):
            update.message.reply_text("你不是BOT管理员，不能使用此命令！")
            return ConversationHandler.END
        reply_keyboard = [['SFW', 'NSFW'], ['R18', '退出']]
        message = "✿✿ヽ（°▽°）ノ✿ 你好！ %s ，请选择你的审核类型" % (user["username"])
        update.message.reply_text(
            message,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return self.EXAMINE

    def setup_handler(self, update: Update, context: CallbackContext) -> int:
        user = update.effective_user
        Log.info("examine: setup函数请求 %s %s" % (user["username"], update.message.text))
        if update.message.text == "退出":
            update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        audit_type = AuditType(update.message.text)
        context.chat_data["audit_type"] = audit_type.value
        count = self.pixiv.audit_start(audit_type)
        reply_keyboard = [['OK', '退出']]
        message = "嗯，我看见了，%s 。审核类型是 %s 吧。\n" \
                  "审核完毕后，可以使用 /push 命令推送。\n" \
                  "接下来进入审核模式，请回复OK继续。" % (user["username"], update.message.text)
        context.user_data["examine_count"] = {
            "count": 0,
            "pass": 0,
            "cancel": 0
        }
        update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.EXAMINE_START

    def cancel_handler(self, update: Update, _: CallbackContext) -> int:
        user = update.message.from_user
        Log.info("User %s canceled the conversation.", user.first_name)
        update.message.reply_text('命令取消.', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def start_handler(self, update: Update, context: CallbackContext) -> int:
        user = update.message.from_user
        Log.info("examine: start函数请求 %s : %s" % (user["username"], update.message.text))
        reply_keyboard = [['通过', '撤销'], ['退出']]
        audit_type = AuditType(context.chat_data.get("audit_type", None))
        if update.message.text == "下一个" or update.message.text == "OK":
            result = self.pixiv.audit_next(audit_type)
            if result is None:
                update.message.reply_text('已经完成了当前的全部审核，退出审核', reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
            artwork_info, images = result
            art_id = artwork_info.art_id
            Log.info("ExamineStart sending photo...")
            context.chat_data["image_key"] = art_id
            url = "https://www.pixiv.net/artworks/%s" % art_id
            caption = "Title %s   \n" \
                      "Views %s Likes %s Loves %s   \n" \
                      "Tags %s   \n" \
                      "From [Pixiv](%s)" % (
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
                    update.message.reply_text("是多张图片的作品呢，要看仔细了哦 ~ ",
                                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
                elif len(images) == 1:
                    photo = images[0].data
                    update.message.reply_photo(photo=photo,
                                               caption=caption,
                                               timeout=30,
                                               parse_mode=ParseMode.MARKDOWN_V2,
                                               reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
                else:
                    Log.error("图片%s获取失败" % art_id)
                    update.message.reply_text("图片获取错误，找开发者背锅吧~")
                    return self.EXAMINE_START
            except BadRequest as TError:
                Log.error("encounter error with image caption\n%s" % caption)
                Log.error(TError)
                return self.EXAMINE_START
            return self.EXAMINE_RESULT
        elif update.message.text == "退出":
            update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        else:
            update.message.reply_text('命令错误，请重新回复')
        return self.EXAMINE_START

    def result_handler(self, update: Update, context: CallbackContext) -> int:
        user = update.message.from_user
        Log.info("examine: result函数请求 %s : %s" % (user["username"], update.message.text))
        if update.message.text == "不够色":
            update.message.reply_text('那你来发嗷！', reply_markup=ReplyKeyboardRemove())
            update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        elif update.message.text == "hso":
            reply_keyboard = [['通过', '撤销'], ['退出']]
            update.message.reply_text('一开口就知道老色批了嗷！', reply_markup=ReplyKeyboardRemove())
            update.message.reply_text('认(g)真(k)点(d)，重新审核嗷！',
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return self.EXAMINE_RESULT
        reply_keyboard = [['下一个', '退出']]
        art_id = context.chat_data.get("image_key", None)
        audit_type = AuditType(context.chat_data.get("audit_type", None))
        if update.message.text == "退出":
            if art_id:
                self.pixiv.audit_cancel(audit_type, art_id)
            update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        elif update.message.text == "通过":
            IsPass = True
        elif update.message.text == "撤销":
            IsPass = False
        else:
            update.message.reply_text('命令错误，请重新回复')
            return self.EXAMINE_RESULT
        if IsPass:
            context.user_data["examine_count"]["count"] += 1
            context.user_data["examine_count"]["pass"] += 1
            self.pixiv.audit_approve(audit_type, art_id)
            remaining = self.pixiv.cache_size(audit_type)
            message = "你选择了：%s，已经确认。你已经审核%s个，通过%s个，撤销%s个。缓存池仍有%s件作品。请选择退出还是下一个。" % (
                update.message.text, context.user_data["examine_count"]["count"],
                context.user_data["examine_count"]["pass"], context.user_data["examine_count"]["cancel"], remaining)
            update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return self.EXAMINE_START
        reply_keyboard = [["质量差", "类型错误"], ["一般"], ["NSFW", "R18"], ["退出"]]
        if audit_type == "NSFW":
            reply_keyboard = [["质量差", "类型错误"], ["一般"], ["R18", "退出"]]
        if audit_type == "R18":
            reply_keyboard = [["质量差", "类型错误"], ["XP兼容性低", "退出"]]
        message = "你选择了：%s，已经确认。请选撤销择原因或者输入原因。" % update.message.text
        update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.EXAMINE_REASON

    def reason_handler(self, update: Update, context: CallbackContext) -> int:
        user = update.message.from_user
        Log.info("examine: reason函数请求 of %s: %s" % (user["username"], update.message.text))
        reply_keyboard = [['下一个', '退出']]
        art_id = context.chat_data.get("image_key", None)
        audit_type = AuditType(context.chat_data.get("audit_type", None))
        if update.message.text == "不够色":
            update.message.reply_text('那你来发嗷！', reply_markup=ReplyKeyboardRemove())
            update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        elif update.message.text == "hso":
            reply_keyboard = [['通过', '撤销'], ['退出']]
            update.message.reply_text('一开口就知道老色批了嗷！', reply_markup=ReplyKeyboardRemove())
            update.message.reply_text('认(g)真(k)点(d)，重新审核嗷！',
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return self.EXAMINE_RESULT
        if update.message.text == "退出":
            if art_id is not None:
                self.pixiv.audit_cancel(audit_type, art_id)
            update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        reason = update.message.text
        self.pixiv.audit_reject(audit_type, art_id, reason)
        remaining = self.pixiv.cache_size(audit_type)
        context.user_data["examine_count"]["count"] += 1
        context.user_data["examine_count"]["cancel"] += 1
        message = "你选择了：%s，已经确认。你已经审核%s个，通过%s个，撤销%s个。缓存池仍有%s件作品。请选择退出还是下一个。" % (
                update.message.text, context.user_data["examine_count"]["count"],
                context.user_data["examine_count"]["pass"], context.user_data["examine_count"]["cancel"], remaining)
        update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.EXAMINE_START
