from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, \
    CallbackQueryHandler

from plugins.download import Download
from plugins.send import SendHandler
from plugins.set_audit import SetAuditHandler
from src.base.config import config
from plugins.contribute import ContributeHandler
from plugins.examine import ExamineHandler
from plugins.push import PushHandler
from plugins.start import start, help_command, test, error_handler
from src.production.pixiv import PixivService
from src.base.logger import Log
from src.base.utils.base import Utils
from src.production.sites.twitter.service import TwitterService

utils = Utils(config)
logger = Log.getLogger()  # 必须在这初始化log 不然...其实也没有到达死机的程度，运行不了不知道为啥


def cancel(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('命令取消.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    Log.info("Start the bot")
    updater = Updater(token=config.TELEGRAM["token"], workers=10)

    dispatcher = updater.dispatcher

    pixiv = PixivService(
        sql_config={
            "host": config.MYSQL["host"],
            "port": config.MYSQL["port"],
            "user": config.MYSQL["user"],
            "password": config.MYSQL["pass"],
            "database": config.MYSQL["database"],
        },
        redis_config={
            "host": config.REDIS["host"],
            "port": config.REDIS["port"],
            "db": config.REDIS["database"],
        },
        px_config={
            "cookie": config.PIXIV["cookie"],
        },
    )

    twitter = TwitterService(sql_config={
        "host": config.MYSQL["host"],
        "port": config.MYSQL["port"],
        "user": config.MYSQL["user"],
        "password": config.MYSQL["pass"],
        "database": config.MYSQL["database"],
    })

    examine = ExamineHandler(pixiv=pixiv)
    examine_handler = ConversationHandler(
        entry_points=[CommandHandler('examine', examine.command_handler, run_async=True)],
        states={
            examine.EXAMINE: [MessageHandler(Filters.text, examine.setup_handler, run_async=True),
                              CommandHandler('skip', examine.skip_handler)],
            examine.EXAMINE_START: [MessageHandler(Filters.text, examine.start_handler, run_async=True),
                                    CommandHandler('skip', examine.skip_handler)],
            examine.EXAMINE_RESULT: [MessageHandler(Filters.text, examine.result_handler, run_async=True),
                                     CommandHandler('skip', examine.skip_handler)],
            examine.EXAMINE_REASON: [MessageHandler(Filters.text, examine.reason_handler, run_async=True),
                                     CommandHandler('skip', examine.skip_handler)],
        },
        fallbacks=[CommandHandler('cancel', examine.cancel_handler, run_async=True)],
    )
    set_audit = SetAuditHandler(pixiv=pixiv)
    set_audit_handler = ConversationHandler(
        entry_points=[CommandHandler('set', set_audit.command_handler, run_async=True)],
        states={
            set_audit.ONE: [
                MessageHandler(Filters.text, set_audit.set_start, run_async=True),
                CommandHandler('skip', cancel)
            ],
            set_audit.TWO: [
                MessageHandler(Filters.text, set_audit.set_operation, run_async=True),
                CommandHandler('skip', cancel)
            ],
            set_audit.THREE: [
                MessageHandler(Filters.text, set_audit.set_audit_info, run_async=True),
                CommandHandler('skip', cancel)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel, run_async=True)],
    )
    push = PushHandler(pixiv=pixiv)
    push_handler = ConversationHandler(
        entry_points=[CommandHandler('push', push.command_handler, run_async=True)],
        states={
            push.ONE: [
                CallbackQueryHandler(push.setup_handler, run_async=True)
            ],
            push.TWO: [
                CallbackQueryHandler(push.start_handler, run_async=True)
            ],
            push.THREE: [
                CallbackQueryHandler(push.end_handler, run_async=True)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel, run_async=True)],
    )

    contribute = ContributeHandler(pixiv=pixiv)
    contribute_handler = ConversationHandler(
        entry_points=[CommandHandler('contribute', contribute.contribute_command, run_async=True)],
        states={
            contribute.ONE: [
                MessageHandler(Filters.text, contribute.ContributeInfo, run_async=True),
                CommandHandler('skip', cancel)
            ],
            contribute.TWO: [
                MessageHandler(Filters.text, contribute.StartContribute, run_async=True),
                CommandHandler('skip', cancel)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel, run_async=True)],
    )
    download = Download(update=updater)
    download_handler = ConversationHandler(
        entry_points=[CommandHandler('download', download.download, run_async=True)],
        states={
            contribute.ONE: [
                MessageHandler(Filters.text, download.start_download, run_async=True),
                CommandHandler('skip', cancel, run_async=True)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel, run_async=True)],
    )
    Send = SendHandler(twitter=twitter)
    send_handler = ConversationHandler(
        entry_points=[CommandHandler('send', Send.send_command, run_async=True)],
        states={
            contribute.ONE: [
                MessageHandler(Filters.text, Send.get_info, run_async=True),
                CommandHandler('skip', cancel)
            ],
            contribute.TWO: [
                MessageHandler(Filters.text, Send.get_channel, run_async=True),
                CommandHandler('skip', cancel)
            ],
            contribute.THREE: [
                MessageHandler(Filters.text, Send.send_message, run_async=True),
                CommandHandler('skip', cancel)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel, run_async=True)],
    )
    dispatcher.add_handler(CommandHandler("start", start, run_async=True))
    dispatcher.add_handler(CommandHandler("help", help_command, run_async=True))
    dispatcher.add_handler(CommandHandler("test", test, run_async=True))
    dispatcher.add_handler(examine_handler)
    dispatcher.add_handler(push_handler)
    dispatcher.add_handler(contribute_handler)
    dispatcher.add_handler(download_handler)
    dispatcher.add_handler(set_audit_handler)
    dispatcher.add_handler(send_handler)
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
