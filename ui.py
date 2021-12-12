import bpy
from .ops import Lattice_Operator,Apply_Lattice_Operator#,Remove_Lattice_Operator


class LATTICE_H_MT_Menus(bpy.types.Menu):
    bl_label = "Lattice Helper"

    def draw(self, context):
        layout = self.layout
        layout.operator(Lattice_Operator.bl_idname)
        layout.operator(Apply_Lattice_Operator.bl_idname,text='应用晶格').mode = 'apply_lattice'
        layout.operator(Apply_Lattice_Operator.bl_idname,text='删除晶格').mode = 'del_lattice'
        #layout.operator(Remove_Lattice_Operator.bl_idname)

def menu_func(self, context):
    support_type = ['LATTICE',"MESH", "CURVE", "FONT", "SURFACE","HAIR","GPENCIL"]

    # self.layout.menu('LATTICE_H_MT_Menus')
    # self.layout.operator_context = 'INVOKE_DEFAULT'
    
    # if len(context.selected_objects)>=2 and context.mode == "EDIT_MESH":
    #     pass
    # else:
    
    selected_objects =  [obj for obj in context.selected_objects if obj.type in support_type] \
                            if context.mode == 'OBJECT' else \
                        [obj for obj in context.selected_objects if obj.type == 'MESH' and context.mode =='EDIT_MESH']
                            #get所有可用物体列表,如果在网格编辑模式则只获取网格的

    modifiers_type = {modifiers.type for obj in selected_objects for modifiers in (obj.modifiers if obj.type !='GPENCIL' else obj.grease_pencil_modifiers)}
    

    # bpy.ops.object.gpencil_modifier_add(type='GP_LATTICE')
    # bpy.ops.object.modifier_add(type='LATTICE')
    
    if ('GP_LATTICE' in modifiers_type or 'LATTICE' in modifiers_type or 'LATTICE' in {obj .type for obj in selected_objects}) and context.mode == 'OBJECT':
        self.layout.column().menu("LATTICE_H_MT_Menus", icon='MOD_LATTICE',)# text="")
    else:        
        self.layout.column().operator(Lattice_Operator.bl_idname)
        
    self.layout.separator()



def menu_register():
    bpy.types.VIEW3D_MT_object_context_menu.prepend(menu_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.prepend(menu_func)

def menu_unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)