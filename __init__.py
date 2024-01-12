import bpy

bl_info = {
    "name": "LatticeHelper",
    'author': 'AIGODLIKE Community: 会飞的键盘侠,小萌新',
    'version': (1, 2),
    'blender': (2, 90, 0),
    'location': '3DView->LatticeHelper',
    'category': 'AIGODLIKE',
}

from .ui import LATTICE_H_MT_Menus, menu_unregister, menu_register
from .ops import Lattice_Operator, AddonPreference,Apply_Lattice_Operator#,Remove_Lattice_Operator
class TranslationHelper():
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
        except(ValueError):
            pass

    def unregister(self):
        bpy.app.translations.unregister(self.name)


# Set
############
from . import zh_CN

LatticeHelper_zh_CN = TranslationHelper('LatticeHelper_zh_CN', zh_CN.data)
LatticeHelper_zh_HANS = TranslationHelper('LatticeHelper_zh_HANS', zh_CN.data, lang='zh_HANS')


clss = [
    LATTICE_H_MT_Menus, 
    Lattice_Operator, 
    AddonPreference,
    Apply_Lattice_Operator,
    # Remove_Lattice_Operator,
        ]


def register():
    for c in clss:
        bpy.utils.register_class(c)
    menu_register()


    if bpy.app.version < (4, 0, 0):
        LatticeHelper_zh_CN.register()
    else:
        LatticeHelper_zh_CN.register()
        LatticeHelper_zh_HANS.register()

def unregister():
    menu_unregister()
    for c in clss:
        bpy.utils.unregister_class(c)


    if bpy.app.version < (4, 0, 0):
        LatticeHelper_zh_CN.unregister()
    else:
        LatticeHelper_zh_CN.unregister()
        LatticeHelper_zh_HANS.unregister()
