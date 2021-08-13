import unittest

from src.base.utils.artid import ExtractArtid


class TestExtractArtid(unittest.TestCase):

    def test_raw_artid_succeeds(self):
        # 1. Setup
        data_list = [
            "85423428",         # only number
            " 85423428"         # with leading space
        ]
        # 2. Execute
        for data in data_list:
            with self.subTest(data=data):
                art_id = ExtractArtid(data)
                # 3. Compare
                self.assertEqual("85423428", art_id)

    def test_http_artwork_url_succeeds(self):
        # 1. Setup
        data_list = [
            "pixiv.net/artworks/85423428",                  # no schema, without `www.`
            "www.pixiv.net/artworks/85423428",              # no schema, with `www.`
            "http://pixiv.net/artworks/85423428",           # http without `www.`
            "http://www.pixiv.net/artworks/85423428",       # http with `www.`
            "https://pixiv.net/artworks/85423428",          # https without `www.`
            "https://www.pixiv.net/artworks/85423428",      # https with `www.`
            "https://www.pixiv.net/artworks/85423428?anything_else=abc",
                                                            # with other params
            " http://pixiv.net/artworks/85423428",          # with leading space
            " http://www.pixiv.net/artworks/85423428 ",     # with trailing space
            "http://www.pixiv.net/artworks/85423428 ",      # with both leading and trailing space
            "http://pixiv.net/member_illust.php?illust_id=85423428"
                                                            # another valid uri
            "http://www.pixiv.net/member_illust.php?illust_id=85423428"
                                                            # with `www.`
            "https://pixiv.net/member_illust.php?mode=medium&illust_id=85423428"
                                                            # with other params
        ]
        # 2. Execute
        for data in data_list:
            with self.subTest(data=data):
                art_id = ExtractArtid(data)
                # 3. Compare
                self.assertEqual("85423428", art_id)
