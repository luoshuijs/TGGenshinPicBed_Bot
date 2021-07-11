import json
import re

def tag_split(tag_str):
    # 1. Split, strip, filter blank
    tags = tag_str.split("#")
    tags = tuple(tag.strip() for tag in tags)
    tags = tuple(tag for tag in tags if len(tag) > 0)
    return tags


class NameMap:
    def __init__(self, data_file):
        with open(data_file) as f:
            self.name_map = json.load(f)
        regex_str_list = []
        for key, value in self.name_map.items():
            # "(?P<Ayaka>Ayaka|神里绫华|Kamisato.*Ayaka)"
            regex_str = "|".join([*value["name"], *value["regex"]])
            regex_str = f"(?P<{key}>{regex_str})"
            regex_str_list.append(regex_str)
        self.regex_str = ".*|.*".join(regex_str_list)
        self.regex_str = f".*{self.regex_str}.*"
        self.tag_regex = re.compile(self.regex_str, re.I)


    def identify_characters(self, tag_str):
        tags = tag_split(tag_str)
        tag_str = "\n".join(tags)
        characters = set()
        for m in self.tag_regex.finditer(tag_str):
            characters = characters.union({key for key, value in m.groupdict().items() if value is not None})
        return characters

    def get_character_names(self, character):
        info = self.name_map.get(character, None)
        if info is not None:
            return tuple(info["name"])
        return tuple()

    def get_multi_character_names(self, characters):
        names = {self.get_character_names(c) for c in characters}
        names = {n for n in names if n != tuple()}
        return names



