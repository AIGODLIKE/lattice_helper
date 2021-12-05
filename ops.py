import bpy
from mathutils import Matrix, Vector
from math import inf
from time import time


class AddonPreference(bpy.types.AddonPreferences):
    bl_idname = __package__
    def_res: bpy.props.IntVectorProperty(name="默认晶格分辨率", default=[2, 2, 2], min=2, max=64)

    items = [('KEY_LINEAR', 'Linear', ''),
             ('KEY_CARDINAL', 'Cardinal', ''),
             ('KEY_CATMULL_ROM', 'Catmull-Rom', ''),
             ('KEY_BSPLINE', 'BSpline', '')]
    
    lerp: bpy.props.EnumProperty(name="插值", items=items,default='KEY_LINEAR')
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "def_res")
        layout.prop(self, "lerp")
        
        
#   添加顶点组
#   在编辑模式整体失效
#   TODO 设置活动项为晶格父级 -编辑模式
#   TODO 设置活动项为其它选中物体父级 -编辑模式 多物体

class Operator(bpy.types.Operator):
    bl_idname = "lthp.op"
    bl_label = "晶格覆盖"
    bl_description = "自动为选中物体添加晶格"
    bl_options = {"REGISTER", "UNDO"}
    
    items = [('KEY_LINEAR', 'Linear', ''),
             ('KEY_CARDINAL', 'Cardinal', ''),
             ('KEY_CATMULL_ROM', 'Catmull-Rom', ''),
             ('KEY_BSPLINE', 'BSpline', '')]
    axis: bpy.props.EnumProperty(name="Axis",
                                 default="Local",
                                 items=[("Local", "Local", ""),
                                        ("Global", "Global", ""),
                                        ("Cursor", "Cursor", "")])
    action: bpy.props.BoolProperty(default=True, name="所有选择物体作为一个整体",description='如果多选物体将作为一个整体添加晶格')
    set_parent: bpy.props.BoolProperty(default=True, name="设置父级",description=
                                       '''如果在物体模式下,将设置晶格为物体的父级
                                        如果在网格编辑模式下,将设置活动物体为晶格父级
                                       ''')
    set_selected_objects_is_active_parent: bpy.props.BoolProperty(default=False, name="设置活动项为其它选中物体父级",description='设置活动项为其它选中物体父级',options={'SKIP_SAVE'})
    
    res: bpy.props.IntVectorProperty(name="Resolution", default=[2, 2, 2], min=2, max=64)
    
    lerp: bpy.props.EnumProperty(name="插值", items=items)
    # new: bpy.props.BoolProperty(default=False, name="新建晶格",)

    def __init__(self) -> None:
        self.res[:] = bpy.context.preferences.addons[__package__].preferences.def_res
        self.lerp = bpy.context.preferences.addons[__package__].preferences.lerp
        self.data = {}
        if bpy.context.mode == "EDIT_MESH":
            self.action=True

    def min_max_calc(self, vertices, mat, box, gtv=None):
        if not gtv:
            def gtv(v): return v
        for v in vertices:
            point = mat @ gtv(v)
            for i in range(3):
                if box[i][0] > point[i]:
                    box[i][0] = point[i]
                if box[i][1] < point[i]:
                    box[i][1] = point[i]

    def box_get_common(self, o: bpy.types.Object, box, mat: Matrix):
        if self.axis == "Local":
            # mat_ = o.rotation_euler.to_matrix().to_4x4().inverted() @ mat
            mat_ = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
            self.min_max_calc(o.bound_box, mat_, box, lambda v: Vector(v))
            # for bpoint in o.bound_box:
            #     bpoint = mat_ @ Vector(bpoint)
            #     for i in range(3):
            #         if box[i][0] > bpoint[i]:
            #             box[i][0] = bpoint[i]
            #         if box[i][1] < bpoint[i]:
            #             box[i][1] = bpoint[i]
        elif self.axis == "Global":
            # m.dot(nli.T).T
            # import numpy as np
            # npm = np.array(mat.to_3x3())
            # nli = [None for _ in range(len(o.data.vertices) * 3)]
            # o.data.vertices.foreach_get("co", nli)
            # nli = np.array(nli).reshape(-1, 3)
            # vertices = npm.dot(nli.T).T + mat.translation
            # box[0][0], box[1][0], box[2][0] = vertices.min(axis=0)
            # box[0][1], box[1][1], box[2][1] = vertices.max(axis=0)
            # vertices.min(axis=1)
            self.min_max_calc(o.data.vertices, mat, box, lambda v: v.co)
            # for bpoint in o.data.vertices:
            #     bpoint = mat @ bpoint.co
            #     for i in range(3):
            #         if box[i][0] > bpoint[i]:
            #             box[i][0] = bpoint[i]
            #         if box[i][1] < bpoint[i]:
            #             box[i][1] = bpoint[i]
        else:
            mat = bpy.context.scene.cursor.rotation_euler.to_matrix().to_4x4().inverted() @ mat
            self.min_max_calc(o.data.vertices, mat, box, lambda v: v.co)
            # for bpoint in o.data.vertices:
            #     bpoint = mat @ bpoint.co
            #     for i in range(3):
            #         if box[i][0] > bpoint[i]:
            #             box[i][0] = bpoint[i]
            #         if box[i][1] < bpoint[i]:
            #             box[i][1] = bpoint[i]

    def box_get_bmesh(self, o: bpy.types.Object, box, mat: Matrix):
        import bmesh
        bm = bmesh.from_edit_mesh(o.data)
        verts = [v for v in bm.verts if v.select]
        if self.axis == "Local":
            mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
        elif self.axis == "Cursor":
            mat = bpy.context.scene.cursor.rotation_euler.to_matrix().to_4x4().inverted() @ mat
        self.min_max_calc(verts, mat, box, lambda v: v.co)

    def box_get(self, o: bpy.types.Object, box=None):
        if not box:
            box = [[inf, -inf] for _ in range(3)]
        if o.name not in self.data:
            self.data[o.name] = {}
        if self.action not in self.data[o.name]:
            self.data[o.name][self.action] = {}
        if self.axis not in self.data[o.name][self.action]:
            self.data[o.name][self.action][self.axis] = box
        else:
            return self.data[o.name][self.action][self.axis]

        mat = o.matrix_world
        if bpy.context.mode == 'EDIT_MESH':
            self.box_get_bmesh(bpy.context.edit_object, box, mat)

        elif o.type != "MESH":
            me = o.to_mesh().copy()
            obj = bpy.data.objects.new(name=me.name, object_data=me)
            bpy.context.collection.objects.link(obj)
            obj.matrix_world = mat
            self.box_get_common(obj, box, mat)
            bpy.data.objects.remove(obj)
        elif o.type == "MESH":
            self.box_get_common(o, box, mat)
        return box
        
    def new_vg(self,obj:bpy.types.Object,name=''):
        vg_name = name + '_LP'                
        
        if vg_name not in obj.vertex_groups:# and bpy.context.mode == "EDIT_MESH"
            obj.vertex_groups.new(name = vg_name)
            print(f'obj {obj}  new vg {vg_name}')
        # C.object.vertex_groups['Suzanne_LP']
        # active = bpy.context.object.active
        # bpy.context.object.vertex_groups.active = C.object.vertex_groups['Suzanne_LP']
        # bpy.context.view_layer.objects.active = D.objects['Suzanne.001']


    def parent_set(self, child: bpy.types.Object, parent: bpy.types.Object,reverse = False):
        bpy.context.view_layer.update()
        if reverse:
            parent.parent = child
            parent.matrix_parent_inverse = child.matrix_world.inverted()
        else:
            child.parent = parent
            child.matrix_parent_inverse = parent.matrix_world.inverted()

    def execute(self, context):
        box = [[inf, -inf] for i in range(3)]
        support_type = ["MESH", "CURVE", "FONT", "SURFACE"]
        active_object = context.active_object
        
        for o in context.selected_objects:
        #     if self.axis == "Local" and context.mode != "EDIT_MESH":
        #         self.axis = "Global"
        
            if o.type not in support_type:
                self.report({"ERROR"}, f"物体{o.name}类型:{o.type}不支持！")
                return {"FINISHED"}

        if self.action:#物体模式 and bpy.context.mode != "EDIT_MESH"
            if self.axis == "Local" and context.mode != "EDIT_MESH":
                self.axis = "Global"
            for o in bpy.context.selected_objects:
                if o.type in support_type:
                    bbox = self.box_get(o, box)
            scale = [(box[1] - box[0]) if abs(box[1] - box[0]) > 0.00000001 else 0.1 for box in bbox]
            location = [(box[1] + box[0]) / 2 for box in bbox]
            lt = bpy.data.lattices.new(name="Group_LP")
            lpo = bpy.data.objects.new(name=lt.name, object_data=lt)
            bpy.context.collection.objects.link(lpo)
            lpo.scale = scale
            if self.axis == "Cursor":
                lpo.rotation_euler = bpy.context.scene.cursor.matrix.to_euler()
                location = bpy.context.scene.cursor.rotation_euler.to_matrix() @ Vector(location)
            lpo.location = location
            lt.interpolation_type_u = lt.interpolation_type_v = lt.interpolation_type_w = self.lerp
            lt.points_u, lt.points_v, lt.points_w = self.res
            for o in bpy.context.selected_objects:
                if o.type in support_type:
                    mod = o.modifiers.new(name="Group_LP", type="LATTICE")
                    mod.object = lpo
                if context.mode == "EDIT_MESH":
                    vg_name = mod.name + '_LP'
                    self.new_vg(obj=o,name=mod.name)
                    # print('new_vg')
                    # bpy.context.object.vertex_groups.get( 'Group')
                    o.vertex_groups.active = o.vertex_groups.get(vg_name)
                    context.view_layer.objects.active = o
                    bpy.ops.object.vertex_group_assign()
                    mod.vertex_group = vg_name
                    # bpy.data.objects["Suzanne"].modifiers["Group_LP"].vertex_group
                    context.view_layer.objects.active = active_object
                    
            if self.set_parent:
                selected_objects = bpy.context.selected_objects[:]
                for so in selected_objects:
                    if so.type in support_type:
                        self.parent_set(so, lpo,reverse=context.mode == "EDIT_MESH")

        else:
            for o in bpy.context.selected_objects[:]:
                if o.type not in support_type:
                    self.report({"ERROR"}, f"物体{o.name}类型:{o.type}不支持！")
                    return {"FINISHED"}
                bbox = self.box_get(o)
                
                lt = bpy.data.lattices.new(name=o.name + "_LP")
                lt.interpolation_type_u = lt.interpolation_type_v = lt.interpolation_type_w = self.lerp                
                lpo = bpy.data.objects.new(name=lt.name, object_data=lt)
                
                
                scale = [(box[1] - box[0]) if abs(box[1] - box[0]) > 0.00000001 else 0.1 for box in bbox]
                location = Vector([(box[1] + box[0]) / 2 for box in bbox])

                if self.axis == "Local":
                    lpo.rotation_euler = o.rotation_euler
                    # lpo.location = o.rotation_euler.to_matrix().to_4x4() @ location
                    mat = o.matrix_world
                    mat_ = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
                    lpo.location = mat @ mat_.inverted() @ location
                elif self.axis == "Cursor":
                    lpo.rotation_euler = bpy.context.scene.cursor.matrix.to_euler()
                    lpo.location = bpy.context.scene.cursor.rotation_euler.to_matrix() @ location
                else:
                    lpo.location = location
                
                lpo.scale = scale

                mod = o.modifiers.new(name=lpo.name, type="LATTICE")
                mod.object = lpo
                bpy.context.collection.objects.link(lpo)
                lt.points_u, lt.points_v, lt.points_w = self.res
                if self.set_parent:
                    self.parent_set(o, lpo,reverse=context.mode == "EDIT_MESH")
                    
                    
                if context.mode == "EDIT_MESH":
                    vg_name = mod.name + '_LP'
                    self.new_vg(obj=o,name=mod.name)
                    # print('new_vg')
                    # bpy.context.object.vertex_groups.get( 'Group')
                    o.vertex_groups.active = o.vertex_groups.get(vg_name)
                    context.view_layer.objects.active = o
                    bpy.ops.object.vertex_group_assign()
                    mod.vertex_group = vg_name
                    # bpy.data.objects["Suzanne"].modifiers["Group_LP"].vertex_group
                    context.view_layer.objects.active = active_object

        def set_selected_objects_is_active_parent():
            if self.set_selected_objects_is_active_parent and len(context.selected_objects)>=2 and context.mode == "EDIT_MESH":
                for o in context.selected_objects:
                    if o!= context.active_object and o.parent == None:
                        # o.parent = active_object
                        self.parent_set(o,active_object)
                        # print('设置父级',o,active_object)
                        # bpy.data.objects["Suzanne"].parent
        set_selected_objects_is_active_parent()
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "axis")
        if context.mode != "EDIT_MESH" :
            layout.prop(self, "action")
        
        layout.prop(self, "set_parent")
        
        if context.mode == "EDIT_MESH"  and len(context.selected_objects)>=2 :
            layout.prop(self, "set_selected_objects_is_active_parent")
        
        layout.prop(self, "res")
        layout.prop(self, "lerp")


if __name__ == "__main__":
    bpy.utils.register_class(Operator)
    bpy.utils.register_class(AddonPreference)

