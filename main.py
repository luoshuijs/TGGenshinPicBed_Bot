from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, \
    CallbackQueryHandler

from plugins.download import Download
from plugins.set_audit import SetAuditHandler
from src.base.config import config
from plugins.contribute import ContributeHandler
from plugins.examine import ExamineHandler
from plugins.push import PushHandler
from plugins.start import start, help_command, test, error_handler
from src.production.pixiv import PixivService
from src.base.logger import Log
from src.base.utils.base import Utils

utils = Utils(config)
logger = Log.getLogger()  # 必须初始化log，不然卡死机


def cancel(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('命令取消.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    Log.info("Start the bot")
    updater = Updater(token=config.TELEGRAM["token"])

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

    examine = ExamineHandler(pixiv=pixiv)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('examine', examine.command_handler)],
        states={
            examine.EXAMINE: [MessageHandler(Filters.text, examine.setup_handler),
                              CommandHandler('skip', examine.skip_handler)],
            examine.EXAMINE_START: [MessageHandler(Filters.text, examine.start_handler),
                                    CommandHandler('skip', examine.skip_handler)],
            examine.EXAMINE_RESULT: [MessageHandler(Filters.text, examine.result_handler),
                                     CommandHandler('skip', examine.skip_handler)],
            examine.EXAMINE_REASON: [MessageHandler(Filters.text, examine.reason_handler),
                                     CommandHandler('skip', examine.skip_handler)],
        },
        fallbacks=[CommandHandler('cancel', examine.cancel_handler)],
    )
    set_audit = SetAuditHandler(pixiv=pixiv)
    set_audit_handler = ConversationHandler(
        entry_points=[CommandHandler('set', set_audit.command_handler)],
        states={
            set_audit.ONE: [
                MessageHandler(Filters.text, set_audit.set_start),
                CommandHandler('skip', cancel)
            ],
            set_audit.TWO: [
                MessageHandler(Filters.text, set_audit.set_operation),
                CommandHandler('skip', cancel)
            ],
            set_audit.THREE: [
                MessageHandler(Filters.text, set_audit.set_audit_info),
                CommandHandler('skip', cancel)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    push = PushHandler(pixiv=pixiv)
    push_handler = ConversationHandler(
        entry_points=[CommandHandler('push', push.command_handler)],
        states={
            push.ONE: [
                CallbackQueryHandler(push.setup_handler)
            ],
            push.TWO: [
                CallbackQueryHandler(push.start_handler)
            ],
            push.THREE: [
                CallbackQueryHandler(push.end_handler)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    contribute = ContributeHandler(pixiv=pixiv)
    contribute_handler = ConversationHandler(
        entry_points=[CommandHandler('contribute', contribute.contribute_command)],
        states={
            contribute.ONE: [
                MessageHandler(Filters.text, contribute.ContributeInfo),
                CommandHandler('skip', cancel)
            ],
            contribute.TWO: [
                MessageHandler(Filters.text, contribute.StartContribute),
                CommandHandler('skip', cancel)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    download = Download(update=updater)
    download_handler = ConversationHandler(
        entry_points=[CommandHandler('download', download.download)],
        states={
            contribute.ONE: [
                MessageHandler(Filters.text, download.start_download),
                CommandHandler('skip', cancel)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("test", test))
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(push_handler)
    dispatcher.add_handler(contribute_handler)
    dispatcher.add_handler(download_handler)
    dispatcher.add_handler(set_audit_handler)
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
