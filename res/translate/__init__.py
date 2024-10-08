import bpy

from . import zh_CN


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


LatticeHelper_zh_CN = TranslationHelper('LatticeHelper_zh_CN', zh_CN.data)
LatticeHelper_zh_HANS = TranslationHelper('LatticeHelper_zh_HANS', zh_CN.data, lang='zh_HANS')


def register():
    if bpy.app.version < (4, 0, 0):
        LatticeHelper_zh_CN.register()
    else:
        LatticeHelper_zh_HANS.register()
        LatticeHelper_zh_CN.register()


def unregister():
    if bpy.app.version < (4, 0, 0):
        LatticeHelper_zh_CN.unregister()
    else:
        LatticeHelper_zh_HANS.unregister()
        LatticeHelper_zh_CN.unregister()
