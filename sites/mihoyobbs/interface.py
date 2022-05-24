import re

from sites import listener


@listener(site_name="mihoyobbs", module_name="ExtractMId")
def ExtractMId(text: str) -> int:
    """
    :param text:
        # https://bbs.mihoyo.com/ys/article/8808224
        # https://m.bbs.mihoyo.com/ys/article/8808224
    :return:
    """
    rgx = re.compile(
        r"(?:bbs\.)?mihoyo\.com/[^.]+/article/(?P<article_id>\d+)")
    matches = rgx.search(text)
    if matches is None:
        return None
    entries = matches.groupdict()
    if entries is None:
        return None
    try:
        art_id = int(entries.get('article_id'))
    except (IndexError, ValueError, TypeError):
        return None
    return art_id
