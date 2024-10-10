bl_info = {
    "name": "Lattice Helper",
    'author': 'AIGODLIKE Community: 会飞的键盘侠,小萌新',
    'version': (1, 2, 2),
    'blender': (2, 90, 0),
    'location': '3DView -> Context Menu -> LatticeHelper',
    'category': 'AIGODLIKE',
}

from . import ui, ops, res, preferences

mods = [
    ui,
    ops,
    res,
    preferences,
]


def register():
    for mod in mods:
        mod.register()


def unregister():
    for mod in mods:
        mod.unregister()
