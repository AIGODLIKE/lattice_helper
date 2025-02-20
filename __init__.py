from . import ui, ops, res, preferences

bl_info = {
    "name": "Lattice Helper",
    "author": "AIGODLIKE Community: 会飞的键盘侠,小萌新",
    "version": (1, 2, 3),
    "blender": (2, 90, 0),
    "location": "3DView -> Context Menu -> LatticeHelper",
    "description": "Add matching lattices to a single or multiple objects in object or editing mode",
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
