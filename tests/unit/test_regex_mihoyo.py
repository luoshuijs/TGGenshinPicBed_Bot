#!/usr/bin/env python3
#
# python3 -m unittest tests.test_regex_mihoyo

import unittest
import re


class TestRegexMihoyo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rgx = re.compile(r"(?:bbs\.)?mihoyo\.com/[^.]+/article/(?P<article_id>\d+)")


    def test_url_should_not_match(self):
        # 1. Setup
        input_url = 'https://ys.mihoyo.com/main/news/detail/21272'
        # 2. Execute
        match = self.rgx.match(input_url)
        # 3. Compare
        self.assertIsNone(match)


    def test_url_should_match(self):
        # 1. Setup
        input_url = 'https://bbs.mihoyo.com/ys/article/8808224'
        # 2. Execute
        match = self.rgx.search(input_url)
        article_id = match.groupdict().get('article_id')
        # 3. Compare
        self.assertEqual(article_id, '8808224')

    def test_url_should_match_mobile(self):
        # 1. Setup
        input_url = 'https://m.bbs.mihoyo.com/ys/article/8808224'
        # 2. Execute
        match = self.rgx.search(input_url)
        article_id = match.groupdict().get('article_id')
        # 3. Compare
        self.assertEqual(article_id, '8808224')
