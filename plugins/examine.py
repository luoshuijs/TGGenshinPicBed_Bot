from typing import Optional, Iterable

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from config import config
from model.artwork import ArtworkInfo, ArtworkImage, AuditInfo, AuditType

from utils.base import Utils
from logger import Log
from utils.markdown import markdown_escape
from service import AuditService, SiteService


class ExamineCount:
    def __init__(self):
        self.all_count: int = 0
        self.pass_count: int = 0
        self.cancel_count: int = 0

    def is_pass(self):
        self.all_count += 1
        self.pass_count += 1

    def is_cancel(self):
        self.all_count += 1
        self.cancel_count += 1


class ExamineHandlerData:
    def __init__(self):
        self.audit_type: AuditType = AuditType.SFW
        self.artwork_info: Optional[ArtworkInfo] = None
        self.artwork_images: Optional[Iterable[ArtworkImage]] = None
        self.audit_info: Optional[AuditInfo] = None


class ExamineHandler:
    EXAMINE, EXAMINE_START, EXAMINE_RESULT, EXAMINE_REASON = range(10200, 10204)

    def __init__(self, site_service: SiteService = None, audit_service: AuditService = None):
        self.utils = Utils(config)
        self.site_service = site_service
        self.audit_service = audit_service

    def command_handler(self, update: Update, context: CallbackContext) -> int:
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
        if context.chat_data.get("examine_handler_data") is None:
            examine_handler_data = ExamineHandlerData()
            context.chat_data["examine_handler_data"] = examine_handler_data
        if context.chat_data.get("examine_count") is None:
            examine_count = ExamineCount()
            context.chat_data["examine_count"] = examine_count
        else:
            examine_count: ExamineCount = context.chat_data.get("examine_count")
            examine_count.__init__()
        return self.EXAMINE

    def setup_handler(self, update: Update, context: CallbackContext) -> int:
        examine_handler_data: ExamineHandlerData = context.chat_data["examine_handler_data"]
        user = update.effective_user
        Log.info("examine: setup函数请求 %s %s" % (user["username"], update.message.text))
        if update.message.text == "退出":
            update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        audit_type = AuditType(update.message.text)
        examine_handler_data.audit_type = audit_type
        count = self.audit_service.audit_start(audit_type)
        if count == 0:
            update.message.reply_text('已经完成了当前的全部审核，退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        reply_keyboard = [['OK', '退出']]
        message = "%s ，目前审核类型是%s 。\n" \
                  "目前缓存池有%s件作品  \n" \
                  "审核完毕后，可以使用 /push 命令推送。\n" \
                  "接下来进入审核模式，请回复OK继续。" % (user["username"], update.message.text, count)
        update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.EXAMINE_START

    def skip_handler(self, update: Update, _: CallbackContext) -> int:
        user = update.message.from_user
        Log.info("User %s canceled the conversation.", user.username)
        update.message.reply_text('命令取消', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def cancel_handler(self, update: Update, _: CallbackContext) -> int:
        user = update.message.from_user
        Log.info("User %s canceled the conversation.", user.username)
        update.message.reply_text('命令取消', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def start_handler(self, update: Update, context: CallbackContext) -> int:
        examine_count: ExamineCount = context.chat_data["examine_count"]
        examine_handler_data: ExamineHandlerData = context.chat_data["examine_handler_data"]
        if self.audit_service.cache_size(examine_handler_data.audit_type) == 0:
            update.message.reply_text('已经完成了当前的全部审核，退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        reply_keyboard = [['通过', '撤销'], ['退出']]
        auto_status: str = ""
        if update.message.text == "下一个" or update.message.text == "OK":
            try:
                result = self.audit_service.audit_next(examine_handler_data.audit_type)
                if result.is_error:
                    reply_keyboard = [['OK', '退出']]
                    update.message.reply_text(f"图片获取错误，返回错误信息为 {result.message}。"
                                              "已经跳过该作品。回复OK继续下一张。",
                                              reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                                               one_time_keyboard=True))
                    return self.EXAMINE_START
                artwork_info = examine_handler_data.artwork_info = result.artwork_info
                artwork_images = examine_handler_data.artwork_images = result.artwork_image
                audit_info = examine_handler_data.audit_info = result.artwork_audit
                audit_count = self.audit_service.get_audit_count(artwork_info)
                audit_count.total_count = audit_count.pass_count + audit_count.reject_count
                if audit_count.total_count >= 5:
                    if examine_handler_data.audit_type == AuditType.SFW:
                        if audit_count.pass_count / audit_count.total_count >= 0.6:
                            auto_status = "通过"
                            examine_count.is_pass()
                            self.audit_service.audit_approve(audit_info, examine_handler_data.audit_type)
                            remaining = self.audit_service.cache_size(examine_handler_data.audit_type)
                            reply_keyboard = []
                        elif audit_count.reject_count / audit_count.total_count >= 0.6:
                            auto_status = "拒绝"
                            examine_count.is_cancel()
                            self.audit_service.audit_reject(examine_handler_data.audit_info,
                                                            examine_handler_data.audit_type, "自动拒绝")
                            remaining = self.audit_service.cache_size(examine_handler_data.audit_type)
                            reply_keyboard = []
                    elif examine_handler_data.audit_type == AuditType.NSFW:
                        if audit_count.reject_count / audit_count.total_count >= 0.6:
                            auto_status = "拒绝"
                            examine_count.is_cancel()
                            self.audit_service.audit_reject(examine_handler_data.audit_info,
                                                            examine_handler_data.audit_type, "自动拒绝")
                            remaining = self.audit_service.cache_size(examine_handler_data.audit_type)
                            reply_keyboard = []
                    elif examine_handler_data.audit_type == AuditType.R18:
                        if audit_count.reject_count / audit_count.total_count >= 0.6:
                            auto_status = "拒绝"
                            examine_count.is_cancel()
                            self.audit_service.audit_reject(examine_handler_data.audit_info,
                                                            examine_handler_data.audit_type, "自动拒绝")
                            remaining = self.audit_service.cache_size(examine_handler_data.audit_type)
                            reply_keyboard = []
                caption = "Title %s   \n" \
                          "%s \n" \
                          "Tags %s   \n" \
                          "From [%s](%s)" % (
                              markdown_escape(artwork_info.title),
                              artwork_info.GetStringStat(),
                              markdown_escape(artwork_info.GetStringTags(filter_character_tags=True)),
                              artwork_info.site_name,
                              artwork_info.origin_url
                          )
                if len(artwork_images) > 1:
                    media = [InputMediaPhoto(media=img_info.data) for img_info in artwork_images]
                    media = media[:10]
                    media[0] = InputMediaPhoto(media=artwork_images[0].data, caption=caption,
                                               parse_mode=ParseMode.MARKDOWN_V2)
                    update.message.reply_media_group(media, timeout=30)
                    update.message.reply_text("是多张图片的作品呢，要看仔细了哦 ~ ",
                                              reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                                               one_time_keyboard=True))
                elif len(artwork_images) == 1:
                    image = artwork_images[0]
                    if image.format == "gif":
                        update.message.reply_animation(animation=image.data,
                                                       caption=caption,
                                                       timeout=30,
                                                       parse_mode=ParseMode.MARKDOWN_V2,
                                                       reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                                                        one_time_keyboard=True))
                    else:
                        update.message.reply_photo(photo=image.data,
                                                   caption=caption,
                                                   timeout=30,
                                                   parse_mode=ParseMode.MARKDOWN_V2,
                                                   reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                                                    one_time_keyboard=True))
                else:
                    Log.error("图片获取失败")
                    reply_keyboard = [['OK', '退出']]
                    update.message.reply_text("图片获取错误，回复OK尝试重新获取",
                                              reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                                               one_time_keyboard=True))
                    return self.EXAMINE_START
            except BadRequest as TError:
                Log.error("encounter error with image caption\n%s" % caption)
                Log.error(TError)
                update.message.reply_text('程序发生致命错误，退出审核', reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
            if auto_status != "":
                update.message.reply_text('已经自动%s，还剩下%s张图片，正在获取下一图片。' % (auto_status, remaining),
                                          reply_markup=ReplyKeyboardRemove())
                return self.start_handler(update, context)
            return self.EXAMINE_RESULT
        elif update.message.text == "退出":
            update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        else:
            update.message.reply_text('命令错误，请重新回复')
        return self.EXAMINE_START

    def result_handler(self, update: Update, context: CallbackContext) -> int:
        examine_count: ExamineCount = context.chat_data["examine_count"]
        examine_handler_data: ExamineHandlerData = context.chat_data["examine_handler_data"]
        if update.message.text == "不够色":
            update.message.reply_text('那你来发嗷！')
            update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        elif update.message.text == "hso":
            reply_keyboard = [['通过', '撤销'], ['退出']]
            update.message.reply_text('一开口就知道老色批了嗷！')
            update.message.reply_text('认(g)真(k)点(d)，重新审核嗷！',
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                                       one_time_keyboard=True))
            return self.EXAMINE_RESULT
        reply_keyboard = [['下一个', '退出']]
        if update.message.text == "退出":
            self.audit_service.audit_cancel(examine_handler_data.audit_info, examine_handler_data.audit_type)
            update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        elif update.message.text == "通过" or update.message.text == "下一个":
            IsPass = True
        elif update.message.text == "撤销":
            IsPass = False
        else:
            update.message.reply_text('命令错误，请重新回复')
            return self.EXAMINE_RESULT
        if IsPass:
            examine_count.is_pass()
            self.audit_service.audit_approve(examine_handler_data.audit_info, examine_handler_data.audit_type)
            remaining = self.audit_service.cache_size(examine_handler_data.audit_type)
            message = "你选择了：%s，已经确认。你已经审核%s个，通过%s个，撤销%s个。" \
                      "缓存池仍有%s件作品。请选择退出还是下一个。" % (
                          update.message.text, examine_count.all_count, examine_count.pass_count,
                          examine_count.cancel_count, remaining)
            if update.message.text == "下一个":
                message = "你已经审核%s个，通过%s个，撤销%s个。缓存池仍有%s件作品。" % (
                    examine_count.all_count, examine_count.pass_count, examine_count.cancel_count, remaining)
                update.message.reply_text(message)
                return self.start_handler(update, context)
            update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return self.EXAMINE_START
        reply_keyboard = [
            ["质量差", "类型错误"],
            ["一般"],
            ["NSFW", "R18"],
            ["退出"]
        ]
        if examine_handler_data.audit_type == AuditType.NSFW:
            reply_keyboard = [
                ["质量差", "类型错误"],
                ["一般"],
                ["R18", "退出"]
            ]
        if examine_handler_data.audit_type == AuditType.R18:
            reply_keyboard = [
                ["质量差", "类型错误"],
                ["一般"],
                ["NSFW", "XP兼容性低"],
                ["退出"]
            ]
        message = "你选择了：%s，已经确认。请选撤销择原因或者输入原因。" % update.message.text
        update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.EXAMINE_REASON

    def reason_handler(self, update: Update, context: CallbackContext) -> int:
        user = update.message.from_user
        examine_count: ExamineCount = context.chat_data["examine_count"]
        examine_handler_data: ExamineHandlerData = context.chat_data["examine_handler_data"]
        reply_keyboard = [['下一个', '退出']]
        if update.message.text == "不够色":
            update.message.reply_text('那你来发嗷！')
            update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        elif update.message.text == "hso":
            reply_keyboard = [['通过', '撤销'], ['退出']]
            update.message.reply_text('一开口就知道老色批了嗷！')
            update.message.reply_text('认(g)真(k)点(d)，重新审核嗷！',
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return self.EXAMINE_RESULT
        if update.message.text == "退出":
            self.audit_service.audit_cancel(examine_handler_data.audit_info, examine_handler_data.audit_type)
            update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        reason = update.message.text
        if reason == "SFW" or reason == "NSFW" or reason == "R18":
            reply_keyboard = [['通过', '撤销'], ['退出']]
            examine_handler_data.audit_info.type = AuditType(reason)
            message = f"你选择了修改作品类型，为 {reason}"
            update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return self.EXAMINE_RESULT
        self.audit_service.audit_reject(examine_handler_data.audit_info,
                                        examine_handler_data.audit_type, reason)
        remaining = self.audit_service.cache_size(examine_handler_data.audit_type)
        examine_count.is_cancel()
        message = "你选择了：%s，已经确认。你已经审核%s个，通过%s个，撤销%s个。缓存池仍有%s件作品。请选择退出还是下一个。" % (
            update.message.text, examine_count.all_count, examine_count.pass_count, examine_count.cancel_count,
            remaining)
        update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.EXAMINE_START
