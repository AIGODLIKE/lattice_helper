import bpy
from mathutils import Matrix, Vector
from math import inf

import bmesh

def get_select_block(obj):
    me = obj.data
    if me.is_editmode:
        bm = bmesh.from_edit_mesh(me)
    else:
        bm = bmesh.new()
        bm.from_mesh(me)
    
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    group_dict = {}#{选择块:{顶点集合}}
    count = 0    
    select_verts = {verts for verts in bm.verts if verts.select}
    select_faces = {face for face in bm.faces if face.select}


    if len(select_faces) <= 4:
        return {0:{v.index for v in bm.verts}}

    while len(select_faces)!=0:
        pop_f = select_faces.pop()
        
        group_dict[pop_f] = [pop_f]
        group_list = group_dict[pop_f]
        f = bm.faces[pop_f.index]
        temp_search = [f]

        while temp_search:
            f = temp_search.pop()
            select_faces.discard(f)
            
            for vert in f.verts:
                if vert in  select_verts:
                    select_verts.remove(vert)
                    # count+=1
                    for link_face in vert.link_faces:
                        if link_face in select_faces and link_face.select:
                            # count+=1
                            group_list.append(link_face)
                            select_faces.discard(link_face)
                            temp_search.append(link_face)
    return {group.index:{v.index for f in group_dict[group] for v in f.verts} for group in  group_dict}

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
#   TODO 在编辑模式下设置晶格会有顶点组位置算法的问题
#   TODO 在一个编辑模式选择多个块，每个块都新建晶格
#   TODO 1物体模式按照集合认定整体
#   TODO 2非网格物体修改器适配（例如给曲线添加阵列在计算的时候没考虑修改器带来的尺寸变化）
#   应用晶格
#   删除晶格

#   在编辑模式内 局部坐标问题
#   获取选择块计算时间问题 3W顶点需要计算30S
#   添加整体边框
class Lattice_Operator(bpy.types.Operator):
    bl_idname = "lthp.op"
    bl_label = "晶格覆盖"
    bl_description = "自动为选中物体添加晶格"
    bl_options = {"REGISTER", "UNDO"}
    
    items = [('KEY_LINEAR', 'Linear', ''),
             ('KEY_CARDINAL', 'Cardinal', ''),
             ('KEY_CATMULL_ROM', 'Catmull-Rom', ''),
             ('KEY_BSPLINE', 'BSpline', '')]
    axis: bpy.props.EnumProperty(name="Axis",
                                 default="Global",
                                 items=[("Local", "Local", ""),
                                        ("Global", "Global", ""),
                                        ("Cursor", "Cursor", "")])
    def update(self,context):            
        if self.edit_axis!= self.axis:
            self.axis = self.edit_axis

    edit_axis: bpy.props.EnumProperty(name="Axis",
                                default="Global",
                                items=[
                                    # ("Local", "Local", ""),
                                    ("Global", "Global", ""),
                                    ("Cursor", "Cursor", "")],
                                update=update)

    # action: bpy.props.BoolProperty(default=True, name="所有选择物体作为一个整体",description='如果多选物体将作为一个整体添加晶格')
    
    set_parent: bpy.props.BoolProperty(default=True, name="设置父级",description=
                                       '''如果在物体模式下,将设置晶格为物体的父级
                                        如果在网格编辑模式下,将设置活动物体为晶格父级
                                       ''')
    
    set_selected_objects_is_active_parent: bpy.props.BoolProperty(default=False, name="设置活动项为其它选中物体父级",description='设置活动项为其它选中物体父级',options={'SKIP_SAVE'})
    
    res: bpy.props.IntVectorProperty(name="Resolution", default=[2, 2, 2], min=2, max=64)
    lerp: bpy.props.EnumProperty(name="插值", items=items)
    
    obj_edit_mode_items = [
        ('whole', '整体', '所有选择物体作为一个整体'),  #物体模式，所有选择作为一个整体， 编辑模式也是所有选择的内容作为一个整体
        ('bound_box', '边界框', '以每一个选择物体的边界框作为一个单独的晶格'),
        # ('individual', '各自', '每一个选择的物体作为一个单独的晶格'),
        ('select_block', '选择块(编辑模式)', '将编辑模式内每一个选择的块作为单独的一个区域添加一个晶格'),        
        ('whole_block', '整个块(编辑模式)', '将编辑模式内所有选择的块作为一个区域添加晶格'),
             ]
    
    use_vert_group: bpy.props.BoolProperty(default=False, name="为修改器指定顶点组",description='根据所选的模式生成顶点组',options={'SKIP_SAVE'})

    obj_edit_mode: bpy.props.EnumProperty(default='bound_box',name="模式", items=obj_edit_mode_items)

    obj_mode_items = [
        ('whole', '整体', '所有选择物体作为一个整体'),  #物体模式，所有选择作为一个整体， 编辑模式也是所有选择的内容作为一个整体
        ('bound_box', '边界框', '以每一个选择物体的边界框作为一个单独的晶格'),
        # # ('individual', '各自', '每一个选择的物体作为一个单独的晶格'),
        # ('select_block', '选择块(编辑模式)', '将编辑模式内每一个选择的块作为单独的一个区域添加一个晶格'),        
        # ('whole_block', '整个块(编辑模式)', '将编辑模式内所有选择的块作为一个区域添加晶格'),
        ]
    
    obj_mode: bpy.props.EnumProperty(default='bound_box',name="模式", items=obj_mode_items)


    def __init__(self) -> None:
        self.res[:] = bpy.context.preferences.addons[__package__].preferences.def_res
        self.lerp = bpy.context.preferences.addons[__package__].preferences.lerp
        # self.data = {}
        
        # if bpy.context.mode == "EDIT_MESH":
        #     obj_edit_mode=True
        # pass
        
        self.objects = {}

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
        return box

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
        if len(verts) <=5:
            verts = [v for v in bm.verts]

        if self.axis == "Local":
            mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
        elif self.axis == "Cursor":
            mat = bpy.context.scene.cursor.rotation_euler.to_matrix().to_4x4().inverted() @ mat
        self.min_max_calc(verts, mat, box, lambda v: v.co)



    def box_get(self, obj: bpy.types.Object,*,whole=False,get_block=False,get_whole_block=False):
        if whole:
            if 'whole' not in  self.objects:
                self.objects['whole'] = []

            for o in obj:                
                mat = o.matrix_world
                cursor = bpy.context.scene.cursor.rotation_euler.to_matrix().to_4x4().inverted() 
                if self.axis == "Local":
                    if o.mode == 'EDIT':
                        # mat = o.rotation_euler.to_matrix().to_4x4() @ mat
                        mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()# @ Matrix.rotate(mat.to_euler()[:]()).to_4x4()
                    else:
                        mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
                elif self.axis == "Cursor":
                    mat = cursor @ mat


        else:
            mat = obj.matrix_world
            cursor = bpy.context.scene.cursor.rotation_euler.to_matrix().to_4x4().inverted() 
            if self.axis == "Local":
                if obj.mode == 'EDIT':
                    # mat = o.rotation_euler.to_matrix().to_4x4() @ mat
                    mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()# @ Matrix.rotate(mat.to_euler()[:]()).to_4x4()
                else:
                    mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()

            elif self.axis == "Cursor":
                mat = cursor @ mat

            if obj not in  self.objects:
                self.objects[obj] = {}
            # else:
            #     return self.objects[o]
            
            
            
            if 'bound_box'not in self.objects[obj]:
                self.objects[obj]['bound_box'] = {}
            if obj.type =='MESH':# and obj.mode != 'OBJECT':#计算网格
                import bmesh
                # bm = bmesh.from_edit_mesh(o.data)
                data = obj.data
                if data.is_editmode:
                    # Gain direct access to the mesh
                    bm = bmesh.from_edit_mesh(data)
                else:
                    bm = bmesh.new()
                    bm.from_mesh(data)

                self.objects[obj]['bound_box']['bound_box'] = self.min_max_calc(vertices = [v for v in bm.verts] , mat = mat, box = [[inf, -inf] for _ in range(3)], gtv =lambda v: v.co)


                if 'block' not in self.objects[obj]:
                    self.objects[obj]['block'] = {}

                if bpy.context.mode == "EDIT_MESH" and get_block:
                    v_block = get_select_block(obj)
                
                    self.objects[obj]['block'] = v_block

                    if 'block' not in self.objects[obj]['bound_box']:
                        self.objects[obj]['bound_box']['block'] = {}
                        
                    for v_ in v_block:
                        verts = [v for v in bm.verts if v.index in v_block[v_]] 
                        self.objects[obj]['bound_box']['block'][str(v_)] = self.min_max_calc(verts, mat, [[inf, -inf] for _ in range(3)], lambda v: v.co)
                
                if get_whole_block:                    
                    if 'whole_block' not in self.objects[obj]['bound_box']:
                        self.objects[obj]['bound_box']['whole_block'] = {}
                    A = [v for v in bm.verts if v.select]
                    if len(A) <=5:
                        A = [v for v in bm.verts]
                    self.objects[obj]['bound_box']['whole_block'] = self.min_max_calc(A, mat, [[inf, -inf] for _ in range(3)], lambda v: v.co)
                    self.objects[obj]['block']['whole_block'] = {i.index for i in A}

            else:#                    
                self.objects[obj]['bound_box']['bound_box'] = self.min_max_calc(obj.bound_box, mat,  [[inf, -inf] for _ in range(3)], lambda v: Vector(v))

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
        support_type = ['LATTICE',"MESH", "CURVE", "FONT", "SURFACE","HAIR","GPENCIL"]
        self.active_object = context.active_object#实例当前活动物体出来备用  添加顶点组用

        self.selected_objects =  [obj for obj in context.selected_objects if obj.type in support_type] \
                                if context.mode == 'OBJECT' else \
                            [obj for obj in context.selected_objects if obj.type == 'MESH' and context.mode =='EDIT_MESH']
                            #get所有可用物体列表,如果在网格编辑模式则只获取网格的

        selected_objects = self.selected_objects
        #self.objects = {物体数据:{
                    # 分块信息(顶点列表):{index:{顶点列表},...},    为修改器指定顶点用
                    # 框信息:{
                        # 边界框:[],
                        # 分块框:[],
                        # 整体框;[]
                        # }}
                    # }
        if len(selected_objects) == 0 :
            self.report({"ERROR"}, f"未选择可添加晶格物体!!")
            return {"FINISHED"}

        def calc(A,B):
            box = [[inf, -inf] for _ in range(3)]
            for _ in range(3):
                
                if A[_][0] >= B[_][0]:
                    box[_][0] = A[_][0]
                else:
                    box[_][0] = B[_][0]
                
                
                if A[_][1] <= B[_][1]:
                    box[_][1] = A[_][1]
                else:
                    box[_][1] = B[_][1]

            return box
        def new_vertex_groups(object,name,vertex_list):
            bpy.ops.object.mode_set(mode='OBJECT',)
            new_name = name+'_LP_VG'
            if new_name not in object.vertex_groups:
                new = object.vertex_groups.new(name=new_name)
            # print(vertex_list)
            new.add(vertex_list,1,'ADD')
            bpy.ops.object.mode_set(mode='EDIT',)
            return new.name
            

        def new_lattices_modifder(object,name,modifder_target,vertex_list):
            if object.type == 'GPENCIL':
                mod = object.grease_pencil_modifiers.new(name=name, type="GP_LATTICE")
            else:
                mod = object.modifiers.new(name=name, type="LATTICE")
            if vertex_list != None:
                mod.vertex_group =  new_vertex_groups(object,name,vertex_list)
            mod.object = bpy.data.objects[modifder_target.name]
            

        def new_lattices_object(object,latticesname_name,scale,location,vertex_list:list=None):
            lt = bpy.data.lattices.new(name=latticesname_name+'_LP')
            lpo = bpy.data.objects.new(name=lt.name, object_data=lt)
            bpy.context.collection.objects.link(lpo)
            # if object.type == 'MESH':
            if self.axis == "Cursor":
                # print(name,'Cursor')

                lpo.rotation_euler = bpy.context.scene.cursor.matrix.to_euler()
                location = bpy.context.scene.cursor.rotation_euler.to_matrix() @ Vector(location)
            
                lpo.scale = scale
                lpo.location = location

            if self.axis == "Local":
                # print(name,'Local')

                if bpy.context.mode == 'EDIT':
                    # mat = o.rotation_euler.to_matrix().to_4x4() @ mat
                    lpo.rotation_euler = object.rotation_euler
                    lpo.location =  object.rotation_euler.to_matrix().to_4x4() @  location
                    # mat = bpy.data.objects[name].matrix_world
                    # mat_ = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
                    lpo.scale = scale
                    # lpo.location = location
                    
                else:
                    lpo.rotation_euler = object.rotation_euler
                    # lpo.location = o.rotation_euler.to_matrix().to_4x4() @ location
                    mat = object.matrix_world
                    mat_ = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
                    lpo.scale = scale
                    lpo.location = location
                # lpo.location = mat @ mat_.inverted() @ location
            
            else:   #全局
                    # print(name,'全局')
                    lpo.scale = scale
                    lpo.location = location
            # else:
            #     lpo.scale = scale
            #     lpo.location = location
            
            lt.interpolation_type_u = lt.interpolation_type_v = lt.interpolation_type_w = self.lerp
            lt.points_u, lt.points_v, lt.points_w = self.res
            new_lattices_modifder(object,lpo.name,lpo,vertex_list = vertex_list)


        obj_edit_mode = self.obj_edit_mode
        obj_mode = self.obj_mode


        EDIT_MESH_MODE = context.mode == "EDIT_MESH"
        OBJECT_MODE =  context.mode == 'OBJECT'
        
        def box_get_(o: bpy.types.Object, box=None):
            if not box:
                box = [[inf, -inf] for _ in range(3)]
            if o.name not in self.data:
                self.data[o.name] = {}
            if obj_edit_mode not in self.data[o.name]:
                self.data[o.name][obj_edit_mode] = {}
            if self.axis not in self.data[o.name][obj_edit_mode]:
                self.data[o.name][obj_edit_mode][self.axis] = box
            else:
                return self.data[o.name][obj_edit_mode][self.axis]

            mat = o.matrix_world
            
            if bpy.context.mode == 'EDIT_MESH':
                for o in selected_objects:
                    self.box_get_bmesh(o, box, mat)

            elif o.type != "MESH":
                self.min_max_calc(o.bound_box, mat,  box, lambda v: Vector(v))
            elif o.type == "MESH":
                self.box_get_common(o, box, mat)
            return box
        
        
        if (obj_edit_mode  == 'whole' and EDIT_MESH_MODE) or (obj_mode ==  'whole' and OBJECT_MODE):
            box = [[inf, -inf] for i in range(3)]
            self.data = {}
            
            for obj in selected_objects:
                bbox = box_get_(obj, box)
                
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

            for o in selected_objects:
                if o.type in support_type:
                    
                    # mod = o.modifiers.new(name="Group_LP", type="LATTICE")
                            
                    if o.type == 'GPENCIL':
                        mod = o.grease_pencil_modifiers.new(name='Group_LP', type="GP_LATTICE")
                    else:
                        mod = o.modifiers.new(name='Group_LP', type="LATTICE")
                
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
                        context.view_layer.objects.active = self.active_object
            
        else:
            for obj in selected_objects:
                self.box_get(obj,
                            get_block= (obj_edit_mode == 'select_block'  and EDIT_MESH_MODE),
                            get_whole_block=  (obj_edit_mode == 'whole_block'  and EDIT_MESH_MODE) or EDIT_MESH_MODE,
                            )                
                bound_box = self.objects[obj]['bound_box']
                if (obj_edit_mode == 'bound_box'  and EDIT_MESH_MODE) or  (obj_mode ==  'bound_box' and OBJECT_MODE):
                    bbox = bound_box['bound_box']
                    scale = [(box[1] - box[0]) if abs(box[1] - box[0]) > 0.00000001 else 0.1 for box in bbox]
                    location = Vector([(box[1] + box[0]) / 2 for box in bbox])
                    new_lattices_object(obj,obj.name,scale,location)
                if obj_edit_mode == 'select_block'  and EDIT_MESH_MODE:
                    A = bound_box['block']
                    for B in A:
                        bbox = A[B]
                        scale = [(box[1] - box[0]) if abs(box[1] - box[0]) > 0.00000001 else 0.1 for box in bbox]
                        location = Vector([(box[1] + box[0]) / 2 for box in bbox])
                        block = self.objects[obj]['block']
                        # print(B,block)
                        # print()
                        
                        new_lattices_object(obj,str(B),scale,location,vertex_list = list(block[int(B)]))
                        # print(B)
                elif obj_edit_mode == 'whole_block'  and EDIT_MESH_MODE:
                    bbox = bound_box['whole_block']
                    scale = [(box[1] - box[0]) if abs(box[1] - box[0]) > 0.00000001 else 0.1 for box in bbox]
                    location = Vector([(box[1] + box[0]) / 2 for box in bbox])
                    block = self.objects[obj]['block']
                    new_lattices_object(obj,obj.name,scale,location,vertex_list = list(block['whole_block']))

                # else:pass
            



        
        # print(self.objects)
        print('____________')
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        if __name__ == "__ma  in__":
            from bpy.types import Panel
            layout=Panel.layout
        # layout.prop(self, "axis",expand=True)
        # layout.prop(self, "mode",expand=True)
        
        if context.mode == "EDIT_MESH":
            layout.prop(self, "edit_axis")#,expand=True)
            layout.prop(self, "obj_edit_mode")#,expand=True)
        else:
            layout.prop(self, "axis")#,expand=True)
            layout.prop(self, "obj_mode")#,expand=True)
        
        layout.prop(self, "res")
        layout.prop(self, "lerp")#,expand=True)


if __name__ == "__main__":
    bpy.utils.register_class(Lattice_Operator)
