from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, \
    CallbackQueryHandler

from plugins.search import SearchHandler
from plugins.contribute import ContributeHandler
from plugins.download import Download
from plugins.errorhandler import error_handler
from plugins.examine import ExamineHandler
from plugins.push import PushHandler
from plugins.send import SendHandler
from plugins.set_audit import SetAuditHandler
from plugins.start import start, help_command, test, ping, unknown_command
from config import config
from logger import Log
from sites import SiteManager
from utils.base import Utils
from service import SiteService, AuditService

utils = Utils(config)


def cancel(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    Log.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('命令取消.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main() -> None:
    Log.info("——————————————————————————————————————")
    Log.info("正在初始化网站管理器")
    manager = SiteManager()
    manager.load()
    Log.info("网站管理器加载成功")
    Log.info("正在初始化网站服务")
    service = SiteService()
    service.set_handlers(manager.get_handlers())
    service.set_config(
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
        pixiv_cookie=config.PIXIV["cookie"]
    )
    service.load()
    Log.info("网站服务加载成功")
    Log.info("正在初始化审核服务")
    audit_service = AuditService(service=service)
    Log.info("初始化审核服务成功")
    Log.info("——————————————————————————————————————")
    """Start the bot."""
    Log.info("Start the bot")
    Log.info("正在启动机器人")
    updater = Updater(token=config.TELEGRAM["token"], workers=10)

    dispatcher = updater.dispatcher
    examine = ExamineHandler(site_service=service, audit_service=audit_service)
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
    set_audit = SetAuditHandler(site_service=service, audit_service=audit_service)
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
    push = PushHandler(site_service=service, audit_service=audit_service)
    push_handler = ConversationHandler(
        entry_points=[CommandHandler('push', push.command_handler, run_async=True)],
        states={
            push.ONE: [
                CallbackQueryHandler(push.setup_handler, run_async=True)
            ],
            push.TWO: [
                CallbackQueryHandler(push.start_handler, run_async=True)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel, run_async=True)]
    )
    contribute = ContributeHandler(site_service=service, audit_service=audit_service)
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
    download = Download()
    download_handler = ConversationHandler(
        entry_points=[CommandHandler('download', download.download, run_async=True)],
        states={
            download.ONE: [
                MessageHandler(Filters.text, download.start_download, run_async=True),
                CommandHandler('skip', cancel, run_async=True)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel, run_async=True)],
    )
    Send = SendHandler(send_service=service)
    send_handler = ConversationHandler(
        entry_points=[CommandHandler('send', Send.send_command, run_async=True)],
        states={
            Send.ONE: [
                MessageHandler(Filters.text, Send.get_info, run_async=True),
                CommandHandler('skip', cancel)
            ],
            Send.TWO: [
                MessageHandler(Filters.text, Send.get_channel, run_async=True),
                CommandHandler('skip', cancel)
            ],
            Send.THREE: [
                MessageHandler(Filters.text, Send.send_message, run_async=True),
                CommandHandler('skip', cancel)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel, run_async=True)],
    )
    search = SearchHandler(site_service=service, audit_service=audit_service)
    search_handler = ConversationHandler(
        entry_points=[CommandHandler('search', search.start, run_async=True)],
        states={
            search.ONE: [
                MessageHandler(Filters.photo, search.get, run_async=True),
                CommandHandler('skip', cancel, run_async=True)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel, run_async=True)],
    )
    dispatcher.add_handler(CommandHandler("start", start, run_async=True))
    dispatcher.add_handler(CommandHandler("help", help_command, run_async=True))
    dispatcher.add_handler(CommandHandler("ping", ping, run_async=True))
    dispatcher.add_handler(CommandHandler("test", test, run_async=True))
    dispatcher.add_handler(examine_handler)
    dispatcher.add_handler(push_handler)
    dispatcher.add_handler(contribute_handler)
    dispatcher.add_handler(download_handler)
    dispatcher.add_handler(set_audit_handler)
    dispatcher.add_handler(send_handler)
    dispatcher.add_handler(search_handler)
    dispatcher.add_handler(MessageHandler((Filters.command & Filters.private), unknown_command, run_async=True))
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
