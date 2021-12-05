import os
from importlib import import_module
from os import path
from typing import Callable
from glob import glob

from logger import Log

SizeHandlers = []


def listener(site_name: str = None, module_name: str = None, **args):
    if site_name is None:
        raise ValueError("Error:Site name is not None")
    if module_name is None:
        raise ValueError("Error:Site module name is not None")

    def decorator(func: Callable):
        SizeHandlers.append(
            (site_name, module_name, func)
        )
        if type(func).__name__ == 'classobj':
            Log.info(f"{site_name} 网站 {module_name} 模块正在导入")
        return site_name

    return decorator


class SiteManager(object):
    def __init__(self):
        self.sites = list()

    def load(self, sites_paths: str = "./sites/*/"):
        # 动态加载
        module_paths = glob(sites_paths)
        for module_path in module_paths:
            module_name = path.basename(path.normpath(module_path))
            if module_name.startswith('__'):
                continue
            if module_name.startswith('base'):
                continue
            Log.info(f"网站管理器找到 {module_name} 网站模块")
            import_module('sites.' + module_name)
            self.sites.append(module_name)

    def get_handlers(self):
        return SizeHandlers
