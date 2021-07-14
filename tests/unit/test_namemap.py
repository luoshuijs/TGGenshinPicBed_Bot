#!/usr/bin/env python3
#
# python3 -m unittest tests.namemap_test

import unittest
import pathlib
import re
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

    def test_namemap_baal(self):
        # 1. Setup
        tag_str_list = [
            "#GenshinImpact#原神#raiden",
            "#原神#GenshinImpact#baal#raiden#魅惑の谷間#Raiden",
            "#原神#Raiden#RaidenShogun#GenshinImpact#女の子",
            "#崩坏3#honkai#女の子#girl#붕괴3rd#GenshinImpact#Raiden#雷电芽衣#原神",
            "#原神#女の子#GenshinImpact#巴尔#Baal#Shogun#雷神#雷神巴尔#baal",
            "#Genshin#原神#温泉#おっぱい#GenshinImpact#原神Project#神里綾華#yoimiya#Raiden",
            "#GenshinImpact#雷電将軍#雷神バアル#Baal#Archon#原神#剣#fanart#game#Raiden",
            "#原神#raiden#魅惑の谷間#タイツ#ストッキング#尻#雷電将軍(原神)",
            "#Baal#雷電将軍#原神#魅惑の谷間#極上の女体#巨乳#원신#おっぱい#極上の乳#雷神巴尔",
            "#R-18#巴尔#雷電将軍#雷神バアル#原神#baal#GenshinImpact#中出し#後背位#断面図",
            "#原神#Genshin#GenshinImpact#miHoYo#baal#raidenshogun#雷電将軍#雷電将軍(原神)#抖M快来#ドMホイホイ",
            "#原神project#GenshinImpact#おっぱい#雷電将軍#baal#原神#雷電将軍(原神)",
            "#GenshinImpact#原神#雷電将軍#RaidenShogun#雷神#おっぱい#輪チラ#雷電将軍(原神)#Baal#巨乳",
            "#原神#GenshinImpact#ฺbaal#雷神バアル#雷電将軍#雷電将軍(原神)",
            "#雷电将军#原神#Genshinimpact#Raidenshogun#Baal#雷電将軍(原神)",
            "#原神#GenshinImpact#雷電将軍#空(原神)#Baal",
            "#R-18#原神#GenshinImpact#雷神バアル#バアル#Baal#おっぱい#巨乳#極上の乳#腋",
        ]
        names_regex = re.compile("#Baal #巴尔", re.I)
        # 2. Execute
        results = tuple(self.name_map.filter_character_tags(tag_str) for tag_str in tag_str_list)
        # 3. Compare
        for tag_str in results:
            with self.subTest(tag_str=tag_str):
                self.assertRegex(tag_str, names_regex)

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
