import bpy


class ApplyLattice(bpy.types.Operator):
    bl_idname = "lthp.apply"
    bl_label = "Apply lattice"
    bl_description = "Automatically apply the lattice modifier"
    bl_options = {"REGISTER", "UNDO"}  #

    mode: bpy.props.EnumProperty(name="Mode",
                                 default="apply_lattice",
                                 items=[
                                     ("apply_lattice", "Apply the lattice modifier", ""),
                                     ("modifier_apply_as_shapekey", "Apply the lattice modifier as a shape key", ""),
                                     (
                                         "keep_modifier_apply_as_shapekey", "Save the lattice modifier as a shape key",
                                         ""),
                                     ("del_lattice", "Delete the lattice modifier", ""),
                                 ])

    del_lattice: bpy.props.BoolProperty(default=True, name="Delete the lattice", description=
    '''When applying or deleting the lattice modifier, remove the specified lattice for the selected lattice or selected objects''')

    del_vg: bpy.props.BoolProperty(default=True, name="Delete the used vertex group", description=
    '''Delete the vertex group used by the lattice modifier, and simultaneously remove the vertex group used by the lattice modifier when applying or deleting it''')

    def execute(self, context):
        self.active_object = context.active_object  # 实例当前活动物体出来备用  添加顶点组用

        support_type = ['LATTICE', "MESH", "CURVE", "SURFACE", "GPENCIL"]  # "FONT",,"HAIR"毛发无法应用修改器

        selected_objects = [obj for obj in context.selected_objects if obj.type in support_type] \
            if context.mode == 'OBJECT' else \
            [obj for obj in context.selected_objects if obj.type == 'MESH' and context.mode == 'EDIT_MESH']

        tmp_del_vg = None
        tmp_del_obj_dict = {}

        print_list = []

        if 'LATTICE' in {obj.type for obj in selected_objects}:
            lattice_objects_list = {obj for obj in selected_objects if obj.type == 'LATTICE'}
            for obj in context.scene.objects:
                context.view_layer.update()
                for mod in (obj.modifiers if obj.type != 'GPENCIL' else obj.grease_pencil_modifiers):
                    if mod.type in ('GP_LATTICE', 'LATTICE') and mod.object != None:
                        if obj.type in support_type:
                            if mod.object in lattice_objects_list:
                                context.view_layer.objects.active = obj
                                if self.del_lattice:
                                    if mod.object not in tmp_del_obj_dict:
                                        tmp_del_obj_dict[mod.object] = []

                                    if obj not in tmp_del_obj_dict[mod.object]:
                                        tmp_del_obj_dict[mod.object].append(obj)

                                if mod.vertex_group in obj.vertex_groups and self.del_vg:  # mod.vertex_group in obj.vertex_groups and
                                    tmp_del_vg = mod.vertex_group

                                if self.mode == 'apply_lattice':
                                    try:
                                        bpy.ops.object.modifier_apply(
                                            modifier=mod.name) if obj.type != 'GPENCIL' else bpy.ops.object.gpencil_modifier_apply(
                                            modifier=mod.name)
                                    except RuntimeError as e:
                                        self.report({"ERROR"}, str(e))
                                elif self.mode == 'del_lattice':
                                    bpy.ops.object.modifier_remove(
                                        modifier=mod.name) if obj.type != 'GPENCIL' else bpy.ops.object.gpencil_modifier_remove(
                                        modifier=mod.name)
                                elif self.mode == 'modifier_apply_as_shapekey' and obj.type != 'GPENCIL':
                                    bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=False, modifier=mod.name)
                                elif self.mode == 'keep_modifier_apply_as_shapekey' and obj.type != 'GPENCIL':
                                    bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=mod.name)
                                if obj.type == 'MESH' and tmp_del_vg != None:
                                    if self.del_vg and tmp_del_vg in obj.vertex_groups:
                                        obj.vertex_groups.remove(obj.vertex_groups[tmp_del_vg])
                                        tmp_del_vg = None
                        else:
                            print_list.append(obj)
                context.view_layer.update()
        else:
            for obj in selected_objects:
                context.view_layer.update()
                for mod in (obj.modifiers if obj.type != 'GPENCIL' else obj.grease_pencil_modifiers):
                    if mod.type in ('GP_LATTICE', 'LATTICE') and mod.object != None:
                        if obj.type in support_type:
                            context.view_layer.objects.active = obj

                            if self.del_lattice:
                                if mod.object not in tmp_del_obj_dict:
                                    tmp_del_obj_dict[mod.object] = []

                                if obj not in tmp_del_obj_dict[mod.object]:
                                    tmp_del_obj_dict[mod.object].append(obj)

                            if mod.vertex_group in obj.vertex_groups and self.del_vg:  # mod.vertex_group in obj.vertex_groups and
                                tmp_del_vg = mod.vertex_group

                            if self.mode == 'apply_lattice':
                                # print(obj,'apply_lattice',mod.name)
                                try:
                                    bpy.ops.object.modifier_apply(
                                        modifier=mod.name) if obj.type != 'GPENCIL' else bpy.ops.object.gpencil_modifier_apply(
                                        modifier=mod.name)
                                except RuntimeError as e:
                                    self.report({"ERROR"}, str(e))
                            elif self.mode == 'del_lattice':
                                # print(obj,'del_lattice',mod.name)
                                bpy.ops.object.modifier_remove(
                                    modifier=mod.name) if obj.type != 'GPENCIL' else bpy.ops.object.gpencil_modifier_remove(
                                    modifier=mod.name)

                            elif self.mode == 'modifier_apply_as_shapekey' and obj.type != 'GPENCIL':
                                bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=False, modifier=mod.name)
                            elif self.mode == 'keep_modifier_apply_as_shapekey' and obj.type != 'GPENCIL':
                                bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=mod.name)

                            if obj.type == 'MESH' and tmp_del_vg != None:

                                if self.del_vg and tmp_del_vg in obj.vertex_groups:
                                    obj.vertex_groups.remove(obj.vertex_groups[tmp_del_vg])
                                    tmp_del_vg = None
                        else:
                            print_list.append(obj)
                context.view_layer.update()

        tmp_obj_mat_dict = {}
        if self.del_lattice:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in tmp_del_obj_dict:
                obj.select_set(True, view_layer=context.view_layer)
                for i in tmp_del_obj_dict[obj]:
                    tmp_obj_mat_dict[i] = i.matrix_world.copy()
                #  A = bpy.context.object.matrix_world.copy()
                # >>> bpy.context.object.matrix_world = A
            bpy.ops.object.delete(use_global=True)

            for obj in tmp_obj_mat_dict:
                obj.matrix_world = tmp_obj_mat_dict[obj]
        if len(print_list) != 0:
            typ = [i.type for i in print_list]
            name = [i.name for i in print_list]
            self.report({"WARNING"},
                        f"Object{name} skip applying the modifier,{typ} type not supported for applying lattice modifier")

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "mode", expand=True)

        row = layout.row()
        row.prop(self, "del_lattice")
        row.prop(self, "del_vg")
