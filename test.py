import bpy
from mathutils import Matrix, Vector


C = bpy.context

A=C.object.matrix_world @  Vector(C.object.bound_box[1][:])