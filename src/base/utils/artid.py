import re

def ExtractArtid(text: str) -> str:
    """
    Extract art_id from the following formats:
        85423428
        pixiv.net/artworks/85423428
        www.pixiv.net/artworks/85423428
        http://pixiv.net/artworks/85423428
        http://www.pixiv.net/artworks/85423428
        https://pixiv.net/artworks/85423428
        https://www.pixiv.net/artworks/85423428
        https://www.pixiv.net/artworks/85423428?anything_else=abc
    """
    rgx = re.compile(r"\s*(?:(?:https?://)?(?:www.)?pixiv.net/(?:artworks/|member_illust.php\?.*illust_id=))?(?P<art_id>[0-9]+).*")
    m = rgx.fullmatch(text)
    if m is None:
        return None
    if "art_id" not in m.groupdict():
        return None
    return m.groupdict()["art_id"]
