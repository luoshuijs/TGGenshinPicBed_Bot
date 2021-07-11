#!/usr/bin/env python3
#
# python3 -m unittest tests.namemap_test

import unittest
import pathlib
from src.production.namemap import NameMap, tag_split


class TestTag(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name_map_file = pathlib.Path(__file__).parent.joinpath("../data/namemap.json").resolve()
        self.name_map = NameMap(self.name_map_file)

    def test_tag_split(self):
        tag_str = "#GenshinImpact#HuTao#Genshin Impact#Hu Tao#Hu Tao (Genshin Impact)"
        tags = ("GenshinImpact", "HuTao", "Genshin Impact", "Hu Tao", "Hu Tao (Genshin Impact)")
        result = tag_split(tag_str)
        self.assertEqual(result, tags)

    def test_namemap(self):
        tag_str = "#GenshinImpact#HuTao#Genshin Impact#Hu Tao#Hu Tao (Genshin Impact)"
        characters = {"Hutao"}
        names = {("Hutao", "胡桃")}
        result = self.name_map.identify_characters(tag_str)
        self.assertEqual(result, characters, msg="%s" % result)
        result = {self.name_map.get_character_names(character) for character in characters}
        self.assertEqual(len(result), 1)
        self.assertEqual(result, names)

    def test_namemap_empty(self):
        tag_str = "#" + "#".join([
            "宝多六花",
            "SSS.GRIDMAN",
            "制服",
            "グリッドマンの下半身担当",
            "NSFW.GRIDMAN",
            "白肌",
            "ベッドファイッ!",
            "半脱ぎ",
            "SSSS.GRIDMAN",
            "SSSS.GRIDMAN50000users入り"
        ])
        characters = set()
        result = self.name_map.identify_characters(tag_str)
        self.assertEqual(result, characters, msg="%s" % result)
        result = {self.name_map.get_character_names(character) for character in characters}
        self.assertEqual(len(result), 0)

    def test_namemap_complex_tag(self):
        tag_str = "#原神#水着#おっぱい#荧#琴#可莉#女の子"
        characters = {"Lumine", "Jean", "Klee"}
        names = {("Lumine", "荧"), ("Jean", "琴"), ("Klee", "可莉")}
        result = self.name_map.identify_characters(tag_str)
        self.assertEqual(result, characters, msg="%s" % result)
        result = {self.name_map.get_character_names(character) for character in characters}
        self.assertEqual(result, names)

    def test_namemap_multi_names(self):
        tag_str = "#GenshinImpact#HuTao#Genshin Impact#Hu Tao#Hu Tao (Genshin Impact)"
        result = self.name_map.identify_characters(tag_str)
        result = self.name_map.get_multi_character_names(result)
        character_names = {("Hutao", "胡桃")}
        self.assertEqual(result, character_names)


if __name__ == "__main__":
    unittest.main()
