import bpy
from .ops import Lattice_Operator


class LATTICE_H_MT_Menus(bpy.types.Menu):
    bl_label = "Lattice Helper"

    def draw(self, context):
        layout = self.layout
        layout.operator(Lattice_Operator.bl_idname)


def menu_func(self, context):
    # self.layout.menu('LATTICE_H_MT_Menus')
    # self.layout.operator_context = 'INVOKE_DEFAULT'

    # if len(context.selected_objects)>=2 and context.mode == "EDIT_MESH":
    #     pass
    # else:
    self.layout.column().operator(Lattice_Operator.bl_idname)
    self.layout.separator()


def menu_register():
    bpy.types.VIEW3D_MT_object_context_menu.prepend(menu_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.prepend(menu_func)


def menu_unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)
