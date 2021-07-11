from src.base.config import config
from src.production.pixiv.pixivwrapper import PixivWrapper

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
