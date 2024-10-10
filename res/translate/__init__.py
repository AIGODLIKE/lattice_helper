import bpy

from . import zh_CN
from ...utils import get_language_list

all_language = get_language_list()


def get_language(language):
    if language not in all_language:
        if bpy.app.version < (4, 0, 0):
            return "zh_CN"
        else:
            return "zh_HANS"
    return language


class TranslationHelper:
    def __init__(self, name: str, data: dict, lang='zh_CN'):
        self.name = name
        self.translations_dict = dict()

        for src, src_trans in data.items():
            key = ("Operator", src)
            self.translations_dict.setdefault(lang, {})[key] = src_trans
            key = ("*", src)
            self.translations_dict.setdefault(lang, {})[key] = src_trans

    def register(self):
        try:
            bpy.app.translations.register(self.name, self.translations_dict)
        except ValueError as e:
            print(e.args)

    def unregister(self):
        bpy.app.translations.unregister(self.name)


LatticeHelper_zh_HANS = TranslationHelper('LatticeHelper_zh_HANS', zh_CN.data, lang=get_language('zh_HANS'))


def register():
    LatticeHelper_zh_HANS.register()


def unregister():
    LatticeHelper_zh_CN.unregister()
