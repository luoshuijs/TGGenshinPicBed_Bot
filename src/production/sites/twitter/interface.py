# 接口
import re


def ExtractTid(text: str) -> int:
    """
    :param text:
    :return:
    # https://twitter.com/i/web/status/1429353251955044356
    # https://twitter.com/abcdefg/status/1429353251955044356
    # https://www.twitter.com/abcdefg/status/1429353251955044356
    # https://mobile.twitter.com/abcdefg/status/1429353251955044356
    """
    rgx = re.compile(
        r"(?:mobile\.|www\.)?twitter\.com/[^.]+/status/(\d+)")
    args = rgx.split(text)
    if args is None:
        return None
    try:
        art_id = int(args[1])
    except (IndexError, ValueError):
        return None
    return art_id



