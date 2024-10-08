import bpy

from .add import AddLattice
from .apply import ApplyLattice


def register():
    bpy.utils.register_class(AddLattice)
    bpy.utils.register_class(ApplyLattice)


def unregister():
    bpy.utils.unregister_class(AddLattice)
    bpy.utils.unregister_class(ApplyLattice)
