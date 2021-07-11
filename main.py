from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, \
    CallbackQueryHandler

from src.base.config import config
from plugins.contribute import StartContribute, contribute_command, ContributeInfo
from plugins.examine import examine, ExamineInfo, ExamineStart, ExamineResult, ExamineReason
from plugins.push import push, PushInfo, StartPush, EndPush
from plugins.start import start, help_command, test
from src.base.logger import Log
from src.base.utils import Utils

utils = Utils(config)
logger = Log.getLogger()

EXAMINE, EXAMINE_START, EXAMINE_RESULT, EXAMINE_REASON = range(4)
ONE, TWO, THREE, FOUR = range(4)

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
        entry_points=[CommandHandler('contribute', contribute_command)],
        states={
            ONE: [
                MessageHandler(Filters.text, ContributeInfo),
                CommandHandler('skip', cancel)
            ],
            TWO: [
                MessageHandler(Filters.text, StartContribute),
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

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
