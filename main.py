from datetime import timedelta, timezone
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot, InlineKeyboardButton, InlineKeyboardMarkup, \
    ParseMode, InputMediaPhoto
from telegram.error import RetryAfter, BadRequest
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, \
    CallbackQueryHandler, run_async
import time

from config import config
from src.logger import Log
from src.utils import Utils
from src.pixiv import PixivWrapper
from src.markdown import markdown_escape

logger = Log.getLogger()

pixiv = PixivWrapper(
    mysql_host=config.MYSQL["host"],
    mysql_port=config.MYSQL["port"],
    mysql_user=config.MYSQL["user"],
    mysql_password=config.MYSQL["pass"],
    mysql_database=config.MYSQL["database"],
    pixiv_cookie=config.PIXIV["cookie"],
    redis_host=config.REDIS["host"],
    redis_port=config.REDIS["port"],
    redis_database=config.REDIS["database"],
)
utils = Utils(config)

EXAMINE, EXAMINE_START, EXAMINE_RESULT, EXAMINE_REASON = range(4)

ONE, TWO, THREE, FOUR = range(4)

logger = Log.getLogger()  # 必须初始化log，不然卡死机


def start(update: Update, _: CallbackContext) -> None:
    user = update.effective_user
    Log.info("start命令请求 user %s id %s" % (user["username"], user["id"]))
    update.message.reply_markdown_v2(fr'✿✿ヽ（°▽°）ノ✿ hi！{user.mention_markdown_v2()}\!')


def test(update: Update, _: CallbackContext) -> None:
    user = update.effective_user
    if not utils.IfOwner(user["id"]):
        return
    Log.info("test命令请求 user %s" % user["username"])
    # pprint.pprint(update.message.date.astimezone(timezone(timedelta(hours=8))))
    # Bot.send_message(chat_id="-1001248064630",text="test20210624")
    update.message.reply_text("pass")


def help_command(update: Update, _: CallbackContext) -> None:
    user = update.effective_user
    if utils.IfOwner(user["id"]):
        message = "亲爱主人你好啊嗷 ✿✿ヽ（°▽°）ノ✿   \n" \
                  "可以使用一下命令   \n" \
                  "内部命令   \n" \
                  "/examine 进入审核  \n" \
                  "/push 推送频道"
    elif utils.IfAdmin(user["id"]):
        message = "好啊嗷 ✿✿ヽ（°▽°）ノ✿   \n" \
                  "可以使用一下命令   \n" \
                  "内部命令   \n" \
                  "/examine 进入审核  \n" \
                  "/push 推送频道"
    else:
        message = "懒得写.jpg"
    update.message.reply_text(message)


def echo(update: Update, _: CallbackContext) -> None:
    if update.message.MESSAGE_TYPES == "text":
        if update.message.text == "不够色":
            update.message.reply_text("那你来发")


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
    logger.info("User %s canceled the conversation.", user.first_name)
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
                    media[0] = InputMediaPhoto(media=artwork.image_list[0], caption=caption, parse_mode=ParseMode.MARKDOWN_V2)
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
    reply_keyboard = [["质量差", "类型错误"], ["一般", "暂定"], ["NSFW", "R18"], ["退出"]]
    if audit_type == "NSFW":
        reply_keyboard = [["质量差", "R18", ], ["类型错误", "退出"]]
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
                        time.sleep(len(media) * 3)
                    elif artwork.count == 1:
                        photo = artwork.image_list[0]
                        sendReq = context.bot.send_photo(char_id, photo, caption=caption,
                                                         parse_mode=ParseMode.MARKDOWN_V2)
                        time.sleep(1)
                except BadRequest as TError:
                    Log.error("encountered error with image caption\n%s" % caption)
                    Log.error(TError)
                    update.message.reply_text("图片发送出错")
                    return ConverationHandler.END
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


def contribute(update: Update, _: CallbackContext) -> int:
    user = update.effective_user
    Log.info("contribute命令请求 user %s id %s" % (user["username"], user["id"]))
    message = "✿✿ヽ（°▽°）ノ✿ 你好！ %s ，欢迎投稿 \n" \
              "当前投稿只支持Pixiv \n" \
              "只需复制URL回复即可 \n" \
              "退出投稿只需回复退出" % (user["username"])
    update.message.reply_text(text=message)


def ContributeInfo(update: Update, context: CallbackContext) -> int:
    if update.message.text == "退出":
        update.message.reply_text(text="退出投稿")
        return ConversationHandler.END
    # 获取作品信息并发送
    reply_keyboard = [['确认', '取消']]
    message = "请确认作品的信息"
    update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return ONE


def StartContribute(update: Update, context: CallbackContext) -> int:
    if update.message.text == "取消":
        update.message.reply_text(text="退出投稿")
        return ConversationHandler.END
    # 写入数据库
    update.message.reply_text('投稿成功', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    Log.info("Start the bot")
    updater = Updater(token=config.TELEGRAM["token"])

    # botinfo = updater.bot.get_me
    # Log.info("bot的名称为：%s" % botinfo["first_name"])

    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('examine', examine)],
        states={
            EXAMINE: [MessageHandler(Filters.text, ExamineInfo),
                      CommandHandler('skip', cancel)],
            EXAMINE_START: [MessageHandler(Filters.text, ExamineStart),
                            CommandHandler('skip', cancel)],
            EXAMINE_RESULT: [MessageHandler(Filters.text, ExamineResult),
                             CommandHandler('skip', cancel)],
            EXAMINE_REASON: [MessageHandler(Filters.text, ExamineReason),
                             CommandHandler('skip', cancel)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    push_handler = ConversationHandler(
        entry_points=[CommandHandler('push', push)],
        states={
            ONE: [
                CallbackQueryHandler(PushInfo)
            ],
            TWO: [
                CallbackQueryHandler(StartPush)
            ],
            THREE: [
                CallbackQueryHandler(EndPush)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    contribute_handler = ConversationHandler(
        entry_points=[CommandHandler('contribute', contribute)],
        states={
            ONE: [
                CallbackQueryHandler(ContributeInfo)
            ],
            TWO: [
                CallbackQueryHandler(StartContribute)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("prpr", prpr))
    dispatcher.add_handler(CommandHandler("hutao", hutao))
    dispatcher.add_handler(CommandHandler("test", test))
    dispatcher.add_handler(CommandHandler("hello", hello))
    dispatcher.add_handler(CommandHandler("sleep", sleep))
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(push_handler)
    dispatcher.add_handler(contribute_handler)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
