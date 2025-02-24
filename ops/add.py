from math import inf

import bmesh
import bpy
from mathutils import Matrix, Vector

from ..utils import get_pref

ADD_LATTICE_OBJECT_MODE_ITEMS = [
    ("WHOLE", "Entirety", "All selected objects as a single entity"),
    ("BOUND_BOX", "Bounding Box", "Use the bounding box of each selected object as a separate lattice"),
]

ADD_LATTICE_OBJECT_EDIT_MODE_ITEMS = [
    *ADD_LATTICE_OBJECT_MODE_ITEMS,
    ("SELECT_BLOCK", "Selection Block (Edit Mode)",
     "Add a lattice for each selected block as a separate region within edit mode"),
    ("WHOLE_BLOCK", "Entire Block (Edit Mode)",
     "Add a lattice for all selected blocks within edit mode as a single region"),
]

GP_TYPES = {"GREASEPENCIL", "GPENCIL"}


def get_select_block(obj):
    me = obj.data
    if me.is_editmode:
        bm = bmesh.from_edit_mesh(me)
    else:
        bm = bmesh.new()
        bm.from_mesh(me)

    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    group_dict = {}  # {选择块:{顶点集合}}
    select_verts = {vert for vert in bm.verts if vert.select}
    select_faces = {face for face in bm.faces if face.select}

    if len(select_faces) <= 4:
        return {0: {v.index for v in bm.verts}}

    while len(select_faces) != 0:
        pop_f = select_faces.pop()

        group_dict[pop_f] = [pop_f]
        group_list = group_dict[pop_f]
        f = bm.faces[pop_f.index]
        temp_search = [f]

        while temp_search:
            f = temp_search.pop()
            select_faces.discard(f)

            for vert in f.verts:
                if vert in select_verts:
                    select_verts.remove(vert)
                    # count+=1
                    for link_face in vert.link_faces:
                        if link_face in select_faces and link_face.select:
                            # count+=1
                            group_list.append(link_face)
                            select_faces.discard(link_face)
                            temp_search.append(link_face)
    return {group.index: {v.index for f in group_dict[group] for v in f.verts} for group in group_dict}


def parent_set(child: bpy.types.Object, parent: bpy.types.Object, reverse=False):
    bpy.context.view_layer.update()
    if reverse:
        parent.parent = child
        parent.matrix_parent_inverse = child.matrix_world.inverted()
    else:
        child.parent = parent
        child.matrix_parent_inverse = parent.matrix_world.inverted()


def new_vertex_group(obj: bpy.types.Object, name=''):
    vg_name = name + '_LP'

    if vg_name not in obj.vertex_groups:
        obj.vertex_groups.new(name=vg_name)


def min_max_calc(vertices, mat, box, gtv=None):
    if not gtv:
        def gtv(v): return v
    for v in vertices:
        point = mat @ gtv(v)
        for i in range(3):
            if box[i][0] > point[i]:
                box[i][0] = point[i]
            if box[i][1] < point[i]:
                box[i][1] = point[i]
    return box


class AddLattice(bpy.types.Operator):
    bl_idname = "object.lattice_helper_add"
    bl_label = "Lattice Add"
    bl_description = "Automatically add a lattice to selected objects"
    bl_options = {"REGISTER", "UNDO"}

    items = [("KEY_LINEAR", "Linear", ""),
             ("KEY_CARDINAL", "Cardinal", ""),
             ("KEY_CATMULL_ROM", "Catmull-Rom", ""),
             ("KEY_BSPLINE", "BSpline", "")]
    axis: bpy.props.EnumProperty(
        name="Axis",
        default="GLOBAL",
        items=[("LOCAL", "Local", ""),
               ("GLOBAL", "Global", ""),
               ("CURSOR", "Cursor", "")])

    def update(self, context):
        if self.edit_axis != self.axis:
            self.axis = self.edit_axis

    edit_axis: bpy.props.EnumProperty(
        name="Axis",
        default="GLOBAL",
        items=[
            # ("LOCAL", "Local", ""),
            ("GLOBAL", "Global", ""),
            ("CURSOR", "Cursor", "")
        ],
        update=update)

    set_parent: bpy.props.BoolProperty(
        default=True,
        name="Set parent",
        description=
        "If in Object Mode, set the lattice as the parent of the object."
        "If in lattice Editing Mode, set the active object as the parent of the lattice"
    )

    set_selected_objects_is_active_parent: bpy.props.BoolProperty(
        default=False,
        name="Set the active item as the parent of other selected objects",
        description="Set the active item as the parent of other selected objects",
        options={"SKIP_SAVE"})

    resolution: bpy.props.IntVectorProperty(name="Resolution", default=[2, 2, 2], min=2, max=64)
    interpolation_type: bpy.props.EnumProperty(name="Interpolation", items=items)

    use_vert_group: bpy.props.BoolProperty(default=False, name="Specify a vertex group for the modifier",
                                           description="Generate a vertex group based on the selected mode",
                                           options={"SKIP_SAVE"})

    add_lattice_edit_mode: bpy.props.EnumProperty(default="SELECT_BLOCK", name="Mode",
                                                  items=ADD_LATTICE_OBJECT_EDIT_MODE_ITEMS)

    add_lattice_object_mode: bpy.props.EnumProperty(default="BOUND_BOX", name="Mode",
                                                    items=ADD_LATTICE_OBJECT_MODE_ITEMS)

    def box_get_common(self, obj: bpy.types.Object, box, mat: Matrix):
        if self.axis == "LOCAL":
            mat_ = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
            min_max_calc(obj.bound_box, mat_, box, lambda v: Vector(v))
        elif self.axis == "GLOBAL":
            min_max_calc(obj.data.vertices, mat, box, lambda v: v.co)
        else:
            mat = bpy.context.scene.cursor.rotation_euler.to_matrix().to_4x4().inverted() @ mat
            min_max_calc(obj.data.vertices, mat, box, lambda v: v.co)

    def box_get_bmesh(self, obj: bpy.types.Object, box, mat: Matrix):
        import bmesh
        vertices_list = []

        def _calc(vertices, box, ):
            for v in vertices:
                point = v
                for i in range(3):
                    if box[i][0] > point[i]:
                        box[i][0] = point[i]
                    if box[i][1] < point[i]:
                        box[i][1] = point[i]
            return box

        for obj in obj:
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            A = [v for v in bm.verts if v.select]
            if len(A) <= 5:
                A = [v for v in bm.verts]
            mat = obj.matrix_world
            if self.axis == "LOCAL":
                mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
            elif self.axis == "CURSOR":
                mat = bpy.context.scene.cursor.rotation_euler.to_matrix().to_4x4().inverted() @ mat
            for b in A:
                vertices_list.append(mat @ b.co)
        _calc(vertices_list, box)

    def box_get(self, obj: bpy.types.Object, *, whole=False, get_block=False, get_whole_block=False):
        if whole:
            if "WHOLE" not in self.objects:
                self.objects["WHOLE"] = []

            for o in obj:
                mat = o.matrix_world
                cursor = bpy.context.scene.cursor.rotation_euler.to_matrix().to_4x4().inverted()
                if self.axis == "LOCAL":
                    if o.mode == "EDIT":
                        mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
                    else:
                        mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
                elif self.axis == "CURSOR":
                    mat = cursor @ mat

        else:
            mat = obj.matrix_world
            cursor = bpy.context.scene.cursor.rotation_euler.to_matrix().to_4x4().inverted()
            if self.axis == "LOCAL":
                if obj.mode == "EDIT":
                    mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
                else:
                    mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()

            elif self.axis == "CURSOR":
                mat = cursor @ mat

            if obj not in self.objects:
                self.objects[obj] = {}

            if "BOUND_BOX" not in self.objects[obj]:
                self.objects[obj]["BOUND_BOX"] = {}
            if obj.type == "MESH":  # 计算网格
                import bmesh
                data = obj.data
                if data.is_editmode:
                    bm = bmesh.from_edit_mesh(data)
                else:
                    bm = bmesh.new()
                    bm.from_mesh(data)

                self.objects[obj]["BOUND_BOX"]["BOUND_BOX"] = min_max_calc(vertices=[v for v in bm.verts], mat=mat,
                                                                           box=[[inf, -inf] for _ in range(3)],
                                                                           gtv=lambda v: v.co)

                if "block" not in self.objects[obj]:
                    self.objects[obj]["block"] = {}

                if bpy.context.mode == "EDIT_MESH" and get_block:
                    v_block = get_select_block(obj)

                    self.objects[obj]["block"] = v_block

                    if "block" not in self.objects[obj]["BOUND_BOX"]:
                        self.objects[obj]["BOUND_BOX"]["block"] = {}

                    for v_ in v_block:
                        verts = [v for v in bm.verts if v.index in v_block[v_]]
                        self.objects[obj]["BOUND_BOX"]["block"][str(v_)] = min_max_calc(verts, mat,
                                                                                        [[inf, -inf] for _ in
                                                                                         range(3)], lambda v: v.co)

                if get_whole_block:
                    if "WHOLE_BLOCK" not in self.objects[obj]["BOUND_BOX"]:
                        self.objects[obj]["BOUND_BOX"]["WHOLE_BLOCK"] = {}
                    A = [v for v in bm.verts if v.select]
                    if len(A) <= 5:
                        A = [v for v in bm.verts]
                    self.objects[obj]["BOUND_BOX"]["WHOLE_BLOCK"] = min_max_calc(A, mat,
                                                                                 [[inf, -inf] for _ in range(3)],
                                                                                 lambda v: v.co)
                    self.objects[obj]["block"]["WHOLE_BLOCK"] = {i.index for i in A}

            else:
                self.objects[obj]["BOUND_BOX"]["BOUND_BOX"] = min_max_calc(obj.bound_box, mat,
                                                                           [[inf, -inf] for _ in range(3)],
                                                                           lambda v: Vector(v))

    def invoke(self, context, event):
        self.selected_objects = None
        self.active_object = None
        self.data = {}
        pref = get_pref()
        self.resolution[:] = pref.resolution
        self.interpolation_type = pref.interpolation_type

        self.objects = {}

        return self.execute(context)

    def execute(self, context):
        support_type = ["LATTICE", "MESH", "CURVE", "FONT", "SURFACE", "GREASEPENCIL", "GPENCIL"]
        self.active_object = context.active_object  # 实例当前活动物体出来备用  添加顶点组用

        self.selected_objects = [obj for obj in context.selected_objects if obj.type in support_type] \
            if context.mode == "OBJECT" else \
            [obj for obj in context.selected_objects if obj.type == "MESH" and context.mode == "EDIT_MESH"]
        # get所有可用物体列表,如果在网格编辑模式则只获取网格的

        add_lattice_edit_mode = self.add_lattice_edit_mode
        add_lattice_object_mode = self.add_lattice_object_mode

        is_edit_mesh_mode = context.mode == "EDIT_MESH"
        is_object_mode = context.mode == "OBJECT"

        selected_objects = self.selected_objects
        # self.objects = {物体数据:{
        # 分块信息(顶点列表):{index:{顶点列表},...},    为修改器指定顶点用
        # 框信息:{
        # 边界框:[],
        # 分块框:[],
        # 整体框;[]
        # }}
        # }
        if len(selected_objects) == 0:
            self.report({"ERROR"}, f"Objects without selection to add lattices!!")
            return {"FINISHED"}

        def new_vertex_groups(obj, name, vertex_list):
            bpy.ops.object.mode_set(mode="OBJECT", )
            new_name = name + "_VG"
            if new_name not in obj.vertex_groups:
                new = obj.vertex_groups.new(name=new_name)
            else:
                new = obj.vertex_groups[new_name]
            new.add(vertex_list, 1, "ADD")
            bpy.ops.object.mode_set(mode="EDIT", )
            context.view_layer.update()
            return new.name

        def new_lattices_modifier(obj, name, modifder_target, vertex_list):
            if obj.type in GP_TYPES:
                if getattr(obj, "grease_pencil_modifiers", False):  # old blender version
                    modifier = obj.grease_pencil_modifiers.new(name=name, type="GP_LATTICE")
                else:
                    modifier = obj.modifiers.new(name=name, type="GREASE_PENCIL_LATTICE")
            else:
                modifier = obj.modifiers.new(name=name, type="LATTICE")
            if vertex_list is not None:
                modifier.vertex_group = new_vertex_groups(obj, name, vertex_list)

            modifier.object = bpy.data.objects[modifder_target.name]
            if self.set_parent:
                parent_set(
                    obj,
                    bpy.data.objects[modifder_target.name],
                    reverse=add_lattice_edit_mode == "SELECT_BLOCK" or add_lattice_edit_mode == "WHOLE_BLOCK"
                )
            context.view_layer.update()
            return modifier

        def new_lattices_object(obj, lattice_name, scale, location, vertex_list: list = None):
            lt = bpy.data.lattices.new(name=lattice_name + "_LP")
            lpo = bpy.data.objects.new(name=lt.name, object_data=lt)
            bpy.context.collection.objects.link(lpo)
            if self.axis == "CURSOR":
                lpo.rotation_euler = bpy.context.scene.cursor.matrix.to_euler()
                location = bpy.context.scene.cursor.rotation_euler.to_matrix() @ Vector(location)

                lpo.scale = scale
                lpo.location = location

            if self.axis == "LOCAL":
                if bpy.context.mode == "EDIT":
                    lpo.rotation_euler = obj.rotation_euler
                    lpo.location = obj.rotation_euler.to_matrix().to_4x4() @ location
                    lpo.scale = scale
                else:
                    lpo.rotation_euler = obj.rotation_euler
                    lpo.scale = scale
                    lpo.location = location

            else:  # 全局
                lpo.scale = scale
                lpo.location = location

            lt.interpolation_type_u = lt.interpolation_type_v = lt.interpolation_type_w = self.interpolation_type
            lt.points_u, lt.points_v, lt.points_w = self.resolution
            new_lattices_modifier(obj, lpo.name, lpo, vertex_list=vertex_list)

            context.view_layer.update()

        def box_get_(o: bpy.types.Object, box):
            mat = o.matrix_world
            if bpy.context.mode == "EDIT_MESH":
                self.box_get_bmesh(selected_objects, box, mat)

            elif o.type != "MESH":
                min_max_calc(o.bound_box, mat, box, lambda v: Vector(v))
            elif o.type == "MESH":
                self.box_get_common(o, box, mat)
            return box

        if (add_lattice_edit_mode == "WHOLE" and is_edit_mesh_mode) or (
                add_lattice_object_mode == "WHOLE" and is_object_mode):
            box = 3 * [[inf, -inf]]

            for obj in selected_objects:
                context.view_layer.update()
                bbox = box_get_(obj, box)
                context.view_layer.update()
            scale = [(box[1] - box[0]) if abs(box[1] - box[0]) > 0.00000001 else 0.1 for box in bbox]
            location = [(box[1] + box[0]) / 2 for box in bbox]
            lattice_data = bpy.data.lattices.new(name="Group_LP")
            lattice_object = bpy.data.objects.new(name=lattice_data.name, object_data=lattice_data)
            bpy.context.collection.objects.link(lattice_object)
            lattice_object.scale = scale
            if self.axis == "CURSOR":
                lattice_object.rotation_euler = bpy.context.scene.cursor.matrix.to_euler()
                location = context.scene.cursor.rotation_euler.to_matrix() @ Vector(location)
            lattice_object.location = location
            lattice_data.interpolation_type_u = lattice_data.interpolation_type_v = lattice_data.interpolation_type_w = self.interpolation_type
            lattice_data.points_u, lattice_data.points_v, lattice_data.points_w = self.resolution

            for obj in selected_objects:
                context.view_layer.update()
                if obj.type in support_type:
                    mod = new_lattices_modifier(obj, "Group_LP", lattice_object, None)

                    if context.mode == "EDIT_MESH":
                        vg_name = mod.name + "_LP"
                        new_vertex_group(obj=obj, name=mod.name)
                        obj.vertex_groups.active = obj.vertex_groups.get(vg_name)
                        context.view_layer.objects.active = obj
                        bpy.ops.object.vertex_group_assign()
                        mod.vertex_group = vg_name
                        context.view_layer.objects.active = self.active_object
                    context.view_layer.update()

        else:
            for obj in selected_objects:
                context.view_layer.update()
                self.box_get(obj,
                             get_block=(add_lattice_edit_mode == "SELECT_BLOCK" and is_edit_mesh_mode),
                             get_whole_block=(
                                                     add_lattice_edit_mode == "WHOLE_BLOCK" and is_edit_mesh_mode) or is_edit_mesh_mode,
                             )
                bound_box = self.objects[obj]["BOUND_BOX"]
                if (add_lattice_edit_mode == "BOUND_BOX" and is_edit_mesh_mode) or (
                        add_lattice_object_mode == "BOUND_BOX" and is_object_mode):
                    context.view_layer.update()
                    bbox = bound_box["BOUND_BOX"]
                    scale = [(box[1] - box[0]) if abs(box[1] - box[0]) > 0.00000001 else 0.1 for box in bbox]
                    location = Vector([(box[1] + box[0]) / 2 for box in bbox])
                    new_lattices_object(obj, obj.name, scale, location)
                if add_lattice_edit_mode == "SELECT_BLOCK" and is_edit_mesh_mode:
                    A = bound_box["block"]
                    for B in A:
                        context.view_layer.update()
                        bbox = A[B]
                        scale = [(box[1] - box[0]) if abs(box[1] - box[0]) > 0.00000001 else 0.1 for box in bbox]
                        location = Vector([(box[1] + box[0]) / 2 for box in bbox])
                        block = self.objects[obj]["block"]

                        new_lattices_object(obj, str(B), scale, location, vertex_list=list(block[int(B)]))
                        context.view_layer.update()
                elif add_lattice_edit_mode == "WHOLE_BLOCK" and is_edit_mesh_mode:
                    context.view_layer.update()
                    bbox = bound_box["WHOLE_BLOCK"]
                    scale = [(box[1] - box[0]) if abs(box[1] - box[0]) > 0.00000001 else 0.1 for box in bbox]
                    location = Vector([(box[1] + box[0]) / 2 for box in bbox])
                    block = self.objects[obj]["block"]
                    new_lattices_object(obj, obj.name, scale, location, vertex_list=list(block["WHOLE_BLOCK"]))
                    context.view_layer.update()
                context.view_layer.update()

        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        if context.mode == "EDIT_MESH":
            layout.prop(self, "edit_axis")
            layout.prop(self, "add_lattice_edit_mode")
        else:
            layout.prop(self, "axis")
            layout.prop(self, "add_lattice_object_mode")
        layout.prop(self, "set_parent")
        layout.prop(self, "resolution")
        layout.prop(self, "interpolation_type")
