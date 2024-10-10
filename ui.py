import bpy

from .ops import AddLattice, ApplyLattice  # ,Remove_Lattice_Operator


class LATTICE_H_MT_Menus(bpy.types.Menu):
    bl_label = "Lattice Helper"

    def draw(self, context):
        layout = self.layout
        layout.operator(AddLattice.bl_idname)
        layout.operator(ApplyLattice.bl_idname, text='Apply lattice').mode = 'apply_lattice'
        layout.operator(ApplyLattice.bl_idname, text='Delete lattice').mode = 'del_lattice'


def menu_draw_func(self, context):
    support_type = ['LATTICE', "MESH", "CURVE", "FONT", "SURFACE", "HAIR", "GPENCIL"]
    is_obj_mode = context.mode == 'OBJECT'
    support_list = [obj for obj in context.selected_objects if obj.type in support_type]
    mesh_list = [obj for obj in context.selected_objects if obj.type == 'MESH' and context.mode == 'EDIT_MESH']
    selected_objects = support_list if is_obj_mode else mesh_list
    # get所有可用物体列表,如果在网格编辑模式则只获取网格的
    modifiers_type = {modifiers.type for obj in selected_objects for modifiers in
                      (obj.modifiers if obj.type != 'GPENCIL' else obj.grease_pencil_modifiers)}
    is_have_lattice_mod = (
                                  'GP_LATTICE' in modifiers_type or
                                  'LATTICE' in modifiers_type or
                                  'LATTICE' in {obj.type for obj in selected_objects}
                          ) and context.mode == 'OBJECT'

    if is_have_lattice_mod:
        self.layout.column().menu("LATTICE_H_MT_Menus", icon='MOD_LATTICE', )
    else:
        ops = self.layout.column().operator(AddLattice.bl_idname)
        if context.mode == "OBJECT":
            ops.obj_mode = "whole"
    self.layout.separator()


def register():
    bpy.utils.register_class(LATTICE_H_MT_Menus)
    bpy.types.VIEW3D_MT_object_context_menu.prepend(menu_draw_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.prepend(menu_draw_func)


def unregister():
    bpy.utils.unregister_class(LATTICE_H_MT_Menus)
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_draw_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_draw_func)
