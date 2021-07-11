import json
import os


class Config(object):
    def __init__(self):
        project_path = os.path.dirname(__file__)
        config_file = os.path.join(project_path, '../../config', 'config.json')
        if not os.path.exists(config_file):
            config_file = os.path.join(project_path, '../../config', 'config.example.json')

        with open(config_file, 'r', encoding='utf-8') as f:
            self.config_json = json.load(f)

        self.ADMINISTRATORS = self.get_config('administrators')
        self.MYSQL = self.get_config('mysql')
        self.REDIS = self.get_config('redis')
        self.PIXIV = self.get_config('pixiv')
        self.TELEGRAM = self.get_config('telegram')

    def get_config(self, name: str):
        # value = os.environ[name] if os.environ.get(name) else self.config_json.get(name, '')
        value = self.config_json.get(name, '')
        return value


config = Config()
