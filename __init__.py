import bpy

bl_info = {
    "name": "Lattice助手",
    'author': '会飞的键盘侠',
    'version': (1, 0),
    'blender': (2, 90, 0),
    'location': '3DView->晶格助手',
    'category': '辣椒出品',
}

from .ui import LATTICE_H_MT_Menus, menu_unregister, menu_register
from .ops import Operator, AddonPreference

clss = [LATTICE_H_MT_Menus, Operator, AddonPreference]


def register():
    for c in clss:
        bpy.utils.register_class(c)
    menu_register()


def unregister():
    menu_unregister()
    for c in clss:
        bpy.utils.unregister_class(c)
    
