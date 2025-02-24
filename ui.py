import bpy

from .ops import AddLattice, ApplyLattice


def draw_add(context: bpy.types.Context, layout: bpy.types.UILayout):
    layout.operator_context = "INVOKE_DEFAULT"
    ops = layout.operator(AddLattice.bl_idname)
    if context.mode == "OBJECT":
        select = len(context.selected_objects)
        if select == 1:
            ops.axis = "LOCAL"
            ops.add_lattice_object_mode = "BOUND_BOX"
        else:
            ops.axis = "GLOBAL"
            ops.add_lattice_object_mode = "WHOLE"


class LATTICE_H_MT_Menus(bpy.types.Menu):
    bl_label = "Lattice Helper"

    def draw(self, context):
        layout = self.layout
        draw_add(context, layout)
        layout.operator(ApplyLattice.bl_idname, text="Apply lattice").mode = "APPLY_LATTICE"
        layout.operator(ApplyLattice.bl_idname, text="Delete lattice").mode = "ONLY_DEL_LATTICE"


def menu_draw_func(self, context):
    support_type = ["LATTICE", "MESH", "CURVE", "FONT", "SURFACE", "GREASEPENCIL", "GPENCIL"]
    is_obj_mode = context.mode == "OBJECT"
    support_list = [obj for obj in context.selected_objects if obj.type in support_type]
    mesh_list = [obj for obj in context.selected_objects if obj.type == "MESH" and context.mode == "EDIT_MESH"]
    selected_objects = support_list if is_obj_mode else mesh_list
    # get所有可用物体列表,如果在网格编辑模式则只获取网格的
    modifiers_type = {modifiers.type for obj in selected_objects for modifiers in
                      (obj.modifiers if obj.type != "GPENCIL" else obj.grease_pencil_modifiers)}
    is_have_lattice_mod = (
                                  "GP_LATTICE" in modifiers_type or
                                  "LATTICE" in modifiers_type or
                                  "LATTICE" in {obj.type for obj in selected_objects}
                          ) and is_obj_mode

    column = self.layout.column(align=True)
    if is_have_lattice_mod:
        column.menu("LATTICE_H_MT_Menus", icon="MOD_LATTICE")
    else:
        draw_add(context, column)
    column.separator()


def register():
    bpy.utils.register_class(LATTICE_H_MT_Menus)
    bpy.types.VIEW3D_MT_object_context_menu.prepend(menu_draw_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.prepend(menu_draw_func)


def unregister():
    bpy.utils.unregister_class(LATTICE_H_MT_Menus)
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_draw_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_draw_func)
