import re
from typing import Optional

from sites import listener


@listener(site_name="pixiv", module_name="ExtractPId")
def ExtractPId(text: str) -> Optional[int]:
    """
    :param text:
        # https://pixiv.net/i/123456
        # https://pixiv.net/artworks/123456
        # https://www.pixiv.net/en/artworks/123456
        # https://www.pixiv.net/member_illust.php?mode=medium&illust_id=123456
    :return: id
    """
    rgx = re.compile(
        r'(?:www\.)?pixiv\.net/(?:en/)?(?:(?:i|artworks)/|member_illust\.php\?(?:mode=[a-z_]*&)?illust_id=)(\d+)')
    args = rgx.split(text)
    if args is None:
        return None
    try:
        art_id = int(args[1])
    except (IndexError, ValueError):
        return None
    return art_id



