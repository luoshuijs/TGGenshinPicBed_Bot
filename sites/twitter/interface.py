import re

from sites import listener


@listener(site_name="twitter", module_name="ExtractTId")
def ExtractTId(text: str) -> int:
    """
    :param text:
        # https://twitter.com/i/web/status/1429353251955044356
        # https://twitter.com/abcdefg/status/1429353251955044356
        # https://www.twitter.com/abcdefg/status/1429353251955044356
        # https://mobile.twitter.com/abcdefg/status/1429353251955044356
    :return:
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



