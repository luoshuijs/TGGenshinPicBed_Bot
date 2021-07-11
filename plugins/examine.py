from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from src.base.config import config

from src.base.utils import Utils
from src.base.logger import Log
from src.production.markdown import markdown_escape
from src.production.pixiv.pixiv import pixiv

utils = Utils(config)

EXAMINE, EXAMINE_START, EXAMINE_RESULT, EXAMINE_REASON = range(4)


def examine(update: Update, _: CallbackContext) -> int:
    user = update.effective_user
    Log.info("examine命令请求 user %s id %s" % (user["username"], user["id"]))
    if not utils.IfAdmin(user["id"]):
        update.message.reply_text("你不是BOT管理员，不能使用此命令！")
        return ConversationHandler.END
    reply_keyboard = [['SFW', 'NSFW'], ['R18', '退出']]
    message = "✿✿ヽ（°▽°）ノ✿ 你好！ %s ，请选择你的审核类型" % (user["username"])
    update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return EXAMINE


def ExamineInfo(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    Log.info("ExamineInfo函数请求 %s %s" % (user["username"], update.message.text))
    pixiv_ = None
    if update.message.text == "退出":
        update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    elif update.message.text == "SFW":
        pixiv_ = pixiv.sfw
        context.chat_data["audit_type"] = "SFW"
    elif update.message.text == "NSFW":
        pixiv_ = pixiv.nsfw
        context.chat_data["audit_type"] = "NSFW"
    elif update.message.text == "R18":
        pixiv_ = pixiv.r18
        context.chat_data["audit_type"] = "R18"
    req = pixiv_.get_v1()
    if not req.status:
        update.message.reply_text('获取数据发生错误，退出审核', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    reply_keyboard = [['OK', '退出']]
    message = "嗯，我看见了，%s 。审核类型是 %s 吧。\n" \
              "审核完毕后，可以使用 /push 命令推送。\n" \
              "接下来进入审核模式，请回复OK继续。" % (user["username"], update.message.text)
    update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return EXAMINE_START


def cancel(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    Log.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('命令取消.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def ExamineStart(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    Log.info("ExamineStart函数请求 %s : %s" % (user["username"], update.message.text))
    reply_keyboard = [['通过', '撤销'], ['退出']]
    audit_type = context.chat_data.get("audit_type", None)
    pixiv_ = None
    if audit_type == "SFW":
        pixiv_ = pixiv.sfw
    elif audit_type == "NSFW":
        pixiv_ = pixiv.nsfw
    elif audit_type == "R18":
        pixiv_ = pixiv.r18
    else:
        raise ValueError("unknown audit_type %s" % audit_type)
    if update.message.text == "下一个" or update.message.text == "OK":
        req = pixiv_.next_v1()
        if req.status:
            if req.data["is_end"]:
                update.message.reply_text('已经完成了当前的全部审核，退出审核', reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END
            Log.info("ExamineStart sending photo...")
            context.chat_data["image_key"] = req.data["img_key"]
            artwork = req.data["img"]
            art_id = req.data["img_info"]["illusts_id"]
            url = "https://www.pixiv.net/artworks/%s" % art_id
            caption = "Title %s   \n" \
                      "Views %s Likes %s Loves %s   \n" \
                      "Tags %s   \n" \
                      "From [Pixiv](%s)" % (
                          markdown_escape(req.data["img_info"]["title"]),
                          req.data["img_info"]["view_count"],
                          req.data["img_info"]["like_count"],
                          req.data["img_info"]["love_count"],
                          markdown_escape(req.data["img_info"]["tags"]),
                          url
                      )
            try:
                if artwork.count > 1:
                    media = [InputMediaPhoto(media=img_data) for img_data in artwork.image_list]
                    media = media[:10]
                    media[0] = InputMediaPhoto(media=artwork.image_list[0], caption=caption,
                                               parse_mode=ParseMode.MARKDOWN_V2)
                    update.message.reply_media_group(media, timeout=30)
                    update.message.reply_text("是多张图片的作品呢，要看仔细了哦 ~ ",
                                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
                elif artwork.count == 1:
                    photo = artwork.image_list[0]
                    update.message.reply_photo(photo=photo,
                                               caption=caption,
                                               timeout=30,
                                               parse_mode=ParseMode.MARKDOWN_V2,
                                               reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
                else:
                    Log.error("图片%s获取失败" % art_id)
                    update.message.reply_text("图片获取错误，找开发者背锅吧~")
                    return EXAMINE_START
            except BadRequest as TError:
                Log.error("encounter error with image caption\n%s" % caption)
                Log.error(TError)
                return EXAMINE_START
            return EXAMINE_RESULT
        else:
            update.message.reply_text('发生错误，错误信息为%s，退出审核' % req.message, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
    elif update.message.text == "退出":
        update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    else:
        update.message.reply_text('命令错误，请重新回复')
    return EXAMINE_START


def ExamineResult(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    Log.info("ExamineResult函数请求 %s : %s" % (user["username"], update.message.text))
    if update.message.text == "不够色":
        update.message.reply_text('那你来发嗷！', reply_markup=ReplyKeyboardRemove())
        update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    elif update.message.text == "hso":
        reply_keyboard = [['通过', '撤销'], ['退出']]
        update.message.reply_text('一开口就知道老色批了嗷！', reply_markup=ReplyKeyboardRemove())
        update.message.reply_text('认(g)真(k)点(d)，重新审核嗷！',
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return EXAMINE_RESULT
    reply_keyboard = [['下一个', '退出']]
    image_key = context.chat_data.get("image_key", None)
    audit_type = context.chat_data.get("audit_type", None)
    pixiv_ = None
    if audit_type == "NSFW":
        pixiv_ = pixiv.nsfw
    elif audit_type == "SFW":
        pixiv_ = pixiv.sfw
    elif audit_type == "R18":
        pixiv_ = pixiv.r18
    else:
        raise ValueError("unknown audit_type %s" % audit_type)
    if update.message.text == "退出":
        if image_key:
            pixiv_.putback_v1(image_key)
        update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    elif update.message.text == "通过":
        IsPass = True
    elif update.message.text == "撤销":
        IsPass = False
    else:
        update.message.reply_text('命令错误，请重新回复')
        return EXAMINE_RESULT
    if IsPass:
        req = pixiv_.ifpsss_v1(result=True, img_key=image_key)
        if not req.status:
            update.message.reply_text('发生错误，错误信息为%s，退出审核' % req.message, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        message = "你选择了：%s，已经确认。请选择退出还是下一个。" % update.message.text
        update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return EXAMINE_START
    reply_keyboard = [["质量差", "类型错误"], ["一般"], ["NSFW", "R18"], ["退出"]]
    if audit_type == "NSFW":
        reply_keyboard = [["质量差", "类型错误"], ["一般"], ["R18", "退出"]]
    if audit_type == "R18":
        reply_keyboard = [["质量差", "类型错误"], ["XP兼容性低", "退出"]]
    message = "你选择了：%s，已经确认。请选撤销择原因或者输入原因。" % update.message.text
    update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return EXAMINE_REASON


def ExamineReason(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    Log.info("ExamineReason函数请求 of %s: %s" % (user["username"], update.message.text))
    reply_keyboard = [['下一个', '退出']]
    image_key = context.chat_data.get("image_key", None)
    audit_type = context.chat_data.get("audit_type", None)
    pixiv_ = None
    if update.message.text == "不够色":
        update.message.reply_text('那你来发嗷！', reply_markup=ReplyKeyboardRemove())
        update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    elif update.message.text == "hso":
        reply_keyboard = [['通过', '撤销'], ['退出']]
        update.message.reply_text('一开口就知道老色批了嗷！', reply_markup=ReplyKeyboardRemove())
        update.message.reply_text('认(g)真(k)点(d)，重新审核嗷！',
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return EXAMINE_RESULT
    if audit_type == "NSFW":
        pixiv_ = pixiv.nsfw
    elif audit_type == "SFW":
        pixiv_ = pixiv.sfw
    elif audit_type == "R18":
        pixiv_ = pixiv.r18
    else:
        raise ValueError("unknown audit_type %s" % audit_type)
    if update.message.text == "退出":
        if image_key:
            pixiv_.putback_v1(image_key)
        update.message.reply_text('退出审核', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    reason = update.message.text
    req = pixiv_.ifpsss_v1(result=False, img_key=image_key, reason=reason)
    if not req.status:
        update.message.reply_text('发生错误，错误信息为%s，退出审核' % req.message, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    message = "你选择了：%s，已经确认。请选择退出还是下一个。" % update.message.text
    update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return EXAMINE_START
