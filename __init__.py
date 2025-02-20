from . import ui, ops, res, preferences

bl_info = {
    "name": "Lattice Helper",
    "author": "AIGODLIKE Community: 会飞的键盘侠,小萌新",
    "version": (1, 2, 3),
    "blender": (2, 90, 0),
    "location": "3DView -> Context Menu -> LatticeHelper",
    "description": "Apply Lattice modifier to object(s) in object/edit mode",
    "category": "AIGODLIKE",
}

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
