import bpy

GP_TYPES = {"GREASEPENCIL", "GPENCIL"}

# "FONT","HAIR"毛发无法应用修改器
SUPPORT_TYPE = ["LATTICE", "MESH", "CURVE", "SURFACE", "GPENCIL", "GREASEPENCIL"]


def remove_lattice_modifier(ops: bpy.types.Operator, obj: bpy.types.Object, mod: bpy.types.Modifier):
    try:
        if obj.type in GP_TYPES:
            if getattr(obj, "grease_pencil_modifiers", False):  # old blender version
                bpy.ops.object.gpencil_modifier_remove(modifier=mod.name)
            else:
                bpy.ops.object.modifier_remove(modifier=mod.name)
        else:
            bpy.ops.object.modifier_remove(modifier=mod.name)
    except RuntimeError as e:
        ops.report({"ERROR"}, str(e))


def apple_lattice_modifier(ops: bpy.types.Operator, obj: bpy.types.Object, mod: bpy.types.Modifier):
    try:
        if obj.type in GP_TYPES:
            if getattr(obj, "grease_pencil_modifiers", False):  # old blender version
                bpy.ops.object.gpencil_modifier_apply(modifier=mod.name)
            else:
                bpy.ops.object.modifier_apply(modifier=mod.name)
        else:
            bpy.ops.object.modifier_apply(modifier=mod.name)
    except RuntimeError as e:
        ops.report({"ERROR"}, str(e))


def get_modifiers(obj: bpy.types.Object) -> list:
    if obj.type in GP_TYPES:
        if getattr(obj, "grease_pencil_modifiers", False):
            return obj.grease_pencil_modifiers
        else:
            return obj.modifiers
    else:
        return obj.modifiers


class ApplyLattice(bpy.types.Operator):
    bl_idname = "object.lattice_helper_apply"
    bl_label = "Apply lattice"
    bl_description = "Automatically apply the lattice modifier"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(
        name="Mode",
        default="APPLY_LATTICE",
        items=[
            ("APPLY_LATTICE", "Apply the lattice modifier", ""),
            ("MODIFIER_APPLY_AS_SHAPEKEY", "Apply the lattice modifier as a shape key", ""),
            ("KEEP_MODIFIER_APPLY_AS_SHAPEKEY", "Save the lattice modifier as a shape key", ""),
            ("ONLY_DEL_LATTICE", "Only Delete the lattice modifier", ""),
        ])

    del_lattice: bpy.props.BoolProperty(
        default=True,
        name="Delete the lattice",
        description="When applying or deleting the lattice modifier, "
                    "remove the specified lattice for the selected lattice or selected objects"
    )

    del_vertex_groups: bpy.props.BoolProperty(
        default=True,
        name="Delete the used vertex group",
        description="Delete the vertex group used by the lattice modifier, "
                    "and simultaneously remove the vertex group used "
                    "by the lattice modifier when applying or deleting it")

    def execute(self, context):
        object_mode_list = [obj for obj in context.selected_objects if obj.type in SUPPORT_TYPE]
        edit_mode_list = [obj for obj in context.selected_objects if obj.type == "MESH"]
        selected_objects = edit_mode_list if context.mode == "EDIT_MESH" else object_mode_list

        tmp_del_obj_dict = {}

        def try_apple_lattice(obj: bpy.types.Object, mod: bpy.types.Modifier):
            lattice_objects_list = {obj for obj in selected_objects if obj.type == "LATTICE"}
            if mod.type in ("GP_LATTICE", "LATTICE") and mod.object is not None:
                if obj.type in SUPPORT_TYPE:
                    if mod.object in lattice_objects_list:
                        context.view_layer.objects.active = obj
                        tmp_del_vg = None

                        if self.del_lattice:
                            if mod.object not in tmp_del_obj_dict:
                                tmp_del_obj_dict[mod.object] = []

                            if obj not in tmp_del_obj_dict[mod.object]:
                                tmp_del_obj_dict[mod.object].append(obj)

                        if mod.vertex_group in obj.vertex_groups and self.del_vertex_groups:
                            tmp_del_vg = mod.vertex_group

                        if self.mode == "APPLY_LATTICE":
                            apple_lattice_modifier(self, obj, mod)

                        elif self.mode == "ONLY_DEL_LATTICE":
                            remove_lattice_modifier(self, obj, mod)

                        elif self.mode == "MODIFIER_APPLY_AS_SHAPEKEY" and obj.type not in GP_TYPES:
                            bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=False, modifier=mod.name)

                        elif self.mode == "KEEP_MODIFIER_APPLY_AS_SHAPEKEY" and obj.type not in GP_TYPES:
                            bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=mod.name)

                        if obj.type == "MESH" and tmp_del_vg is not None:
                            if self.del_vertex_groups and tmp_del_vg in obj.vertex_groups:
                                obj.vertex_groups.remove(obj.vertex_groups[tmp_del_vg])

        if "LATTICE" in {obj.type for obj in selected_objects}:
            for obj in context.scene.objects:
                for mod in get_modifiers(obj):
                    try_apple_lattice(obj, mod)
                context.view_layer.update()
        else:
            for obj in selected_objects:
                for mod in get_modifiers(obj):
                    if mod.type in ("GP_LATTICE", "LATTICE") and mod.object is not None:
                        try_apple_lattice(obj, mod)
                context.view_layer.update()

        if self.del_lattice:
            object_matrix_dict_copy = {}
            bpy.ops.object.select_all(action="DESELECT")
            for obj in tmp_del_obj_dict:
                obj.select_set(True, view_layer=context.view_layer)
                for i in tmp_del_obj_dict[obj]:
                    object_matrix_dict_copy[i] = i.matrix_world.copy()
            bpy.ops.object.delete(use_global=True)

            for obj in object_matrix_dict_copy:
                obj.matrix_world = object_matrix_dict_copy[obj]
                context.view_layer.update()

        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "mode", expand=True)

        row = layout.row()
        row.prop(self, "del_lattice")
        row.prop(self, "del_vertex_groups")
