import re


def MxtractTid(text: str) -> int:
    """
    :param text:
        # https://bbs.mihoyo.com/ys/article/8808224
    :return:
    """
    rgx = re.compile(
        r"(?:bbs\.)?mihoyo\.com/[^.]+/article/(\d+)")
    args = rgx.split(text)
    if args is None:
        return None
    try:
        art_id = int(args[1])
    except (IndexError, ValueError):
        return None
    return art_id



