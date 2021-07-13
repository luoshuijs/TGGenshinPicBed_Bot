#!/usr/bin/env python3
#
# python3 -m unittest tests.namemap_test

import unittest
import pathlib
from src.production.namemap import NameMap, tag_split


class TestTag(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        name_map_file = pathlib.Path(__file__).parent.joinpath("../../data/namemap.json").resolve()
        cls.name_map = NameMap(name_map_file)

    def test_tag_split(self):
        # 1. Setup
        sut = "#GenshinImpact#HuTao#Genshin Impact#Hu Tao#Hu Tao (Genshin Impact)"
        tags = ("GenshinImpact", "HuTao", "Genshin Impact", "Hu Tao", "Hu Tao (Genshin Impact)")
        # 2. Execute
        result = tag_split(sut)
        # 2. Compare
        self.assertEqual(result, tags)

    def test_namemap_hutao(self):
        # 1. Setup
        tag_str = "#GenshinImpact#HuTao#Genshin Impact#Hu Tao#Hu Tao (Genshin Impact)"
        characters = {"Hutao"}
        names = {("Hutao", "胡桃")}
        # 2. Execute
        char_result = self.name_map.identify_characters(tag_str)
        name_result = {self.name_map.get_character_names(character) for character in characters}
        # 3. Compare
        self.assertEqual(char_result, characters, msg="%s" % char_result)
        self.assertEqual(name_result, names)

    def test_namemap_ayaka(self):
        # 1. Setup
        tag_str = "#神里#GenshinImpact#原神"
        characters = {"Ayaka"}
        names = {("Ayaka", "神里绫华")}
        # 2. Execute
        char_result = self.name_map.identify_characters(tag_str)
        name_result = {self.name_map.get_character_names(character) for character in characters}
        # 3. Compare
        self.assertEqual(char_result, characters, msg="%s" % char_result)
        self.assertEqual(name_result, names)

    def test_namemap_empty(self):
        # 1. Setup
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
        names = set()
        # 2. Execute
        char_result = self.name_map.identify_characters(tag_str)
        name_result = {self.name_map.get_character_names(character) for character in characters}
        # 3. Compare
        self.assertEqual(char_result, characters, msg="%s" % char_result)
        self.assertEqual(name_result, names)

    def test_namemap_white_space_tag(self):
        # 1. Setup
        tag_str = "#原神 #水着 #おっぱい #荧 #琴 #可莉 #女の子"
        characters = {"Lumine", "Jean", "Klee"}
        names = {("Lumine", "荧"), ("Jean", "琴"), ("Klee", "可莉")}
        # 2. Execute
        char_result = self.name_map.identify_characters(tag_str)
        name_result = {self.name_map.get_character_names(character) for character in characters}
        # 3. Compare
        self.assertEqual(char_result, characters, msg="%s" % char_result)
        self.assertEqual(name_result, names)

    def test_namemap_multi_names(self):
        # 1. Setup
        tag_str = "#GenshinImpact#HuTao#Genshin Impact#Hu Tao#Hu Tao (Genshin Impact)"
        # 2. Execute
        result = self.name_map.identify_characters(tag_str)
        result = self.name_map.get_multi_character_names(result)
        # 3. Compare
        character_names = {("Hutao", "胡桃")}
        self.assertEqual(result, character_names)
