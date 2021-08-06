from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from src.base.logger import Log
from src.base.config import config
from src.base.utils.markdown import markdown_escape
from src.production.pixiv import PixivService
from src.production.pixiv.downloader import PixivDownloader
from src.production.contribute import Contribute


class ContributeHandler:
    ONE, TWO, THREE, FOUR = range(4)

    def __init__(self, pixiv: PixivService = None):
        self.downloader = PixivDownloader(cookie=config.PIXIV["cookie"])
        self.contribute = Contribute()
        self.pixiv = pixiv

    def contribute_command(self, update: Update, _: CallbackContext) -> int:
        user = update.effective_user
        Log.info("contribute命令请求 user %s id %s" % (user["username"], user["id"]))
        message = "✿✿ヽ（°▽°）ノ✿ 你好！ %s ，欢迎投稿 \n" \
                  "当前投稿只支持Pixiv \n" \
                  "只需复制URL回复即可 \n" \
                  "退出投稿只需回复退出" % (user["username"])
        update.message.reply_text(text=message)
        return self.ONE

    def ContributeInfo(self, update: Update, context: CallbackContext) -> int:
        if update.message.text == "退出":
            update.message.reply_text(text="退出投稿")
            return ConversationHandler.END
        # 获取作品信息并发送
        Rsq = self.contribute.GetIllustsID(update.message.text)
        if not Rsq.status:
            message = "获取作品信息失败，请检连接或者ID是否有误"
            update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        art_id = Rsq.data
        artwork_data = self.pixiv.contribute_start(art_id)
        if artwork_data is None:  # 作品存在数据库返回None
            update.message.reply_text("插画已在频道或者数据库，退出投稿")  #
            return ConversationHandler.END
        artwork_info, images = artwork_data
        Log.info("用户 %s 请求投稿作品 id: %s" % (update.effective_user.username, Rsq.data))
        if artwork_info is None:
            update.message.reply_text("插画信息获取错误，找开发者背锅吧~")
            return ConversationHandler.END
        if not "原神" in artwork_info.tags:
            update.message.reply_text("插画标签不符合投稿要求，如果确认没问题请联系管理员")
            return ConversationHandler.END
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
            elif len(images) == 1:
                photo = images[0].data
                update.message.reply_photo(photo=photo,
                                           caption=caption,
                                           timeout=30,
                                           parse_mode=ParseMode.MARKDOWN_V2)
            else:
                Log.error("图片%s获取失败" % art_id)
                update.message.reply_text("图片获取错误，找开发者背锅吧~")  # excuse?
                return ConversationHandler.END
        except BadRequest as TError:
            update.message.reply_text("图片获取错误，找开发者背锅吧~")
            Log.error("encounter error with image caption\n%s" % caption)
            Log.error(TError)
            return ConversationHandler.END
        context.chat_data["contribute_art_id"] = art_id
        reply_keyboard = [['确认', '取消']]
        message = "请确认作品的信息"
        update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return self.TWO

    def StartContribute(self, update: Update, context: CallbackContext) -> int:
        if update.message.text == "取消":
            update.message.reply_text(text="退出投稿")
            return ConversationHandler.END
        art_id = context.chat_data["contribute_art_id"]
        self.pixiv.contribute_confirm(art_id)
        update.message.reply_text('投稿成功！✿✿ヽ（°▽°）ノ✿', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
