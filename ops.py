import bpy
from mathutils import Matrix, Vector
from math import inf
from time import time

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader

import bmesh

def draw_callback_px(self, context):
    print("mouse points", len(self.mouse_path))

    font_id = 0  # XXX, need to find out how best to get this.

    # draw some text
    blf.position(font_id, 15, 30, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Hello Word " + str(len(self.mouse_path)))

    # 50% alpha, 2 pixel width line
    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')
    gpu.state.line_width_set(2.0)
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": self.mouse_path})
    shader.bind()
    shader.uniform_float("color", (0.0, 0.0, 0.0, 0.5))
    batch.draw(shader)

    # restore opengl defaults
    gpu.state.line_width_set(2.0)
    gpu.state.blend_set('NONE')

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

def draw_3d(self,data):
    import bpy
    import gpu
    from gpu_extras.batch import batch_for_shader
    data = [j for i in data for j in i]
    # print(data)
    
    x =data[0]
    _x =data[1]
    y = data[2]
    _y = data[3]
    z =data[4]
    _z = data[5]
    coords = (
        (_x, _y, _z), (x, _y, _z),
        (_x, y, _z), (x, y, _z),
        (_x, _y, z), (x, _y, z),
        (_x, y, z), (x, y, z))

    # coords = (
    #     (-1, -1, -1), (+1, -1, -1),
    #     (-1, +1, -1), (+1, +1, -1),
    #     (-1, -1, +1), (+1, -1, +1),
    #     (-1, +1, +1), (+1, +1, +1))

    indices = (
        (0, 1), (0, 2), (1, 3), (2, 3),
        (4, 5), (4, 6), (5, 7), (6, 7),
        (0, 4), (1, 5), (2, 6), (3, 7))

    shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)


    def draw():
        shader.bind()
        shader.uniform_float("color", (1, 0, 0, 1))
        batch.draw(shader)
        
    return draw

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
#   

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
                                 default="Local",
                                 items=[("Local", "Local", ""),
                                        ("Global", "Global", ""),
                                        ("Cursor", "Cursor", "")])
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
        # self.res[:] = bpy.context.preferences.addons[__package__].preferences.def_res
        # self.lerp = bpy.context.preferences.addons[__package__].preferences.lerp
        # self.data = {}
        
        # if bpy.context.mode == "EDIT_MESH":
        #     self.action=True
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

    def box_get_bmesh(self, o: bpy.types.Object, box, mat: Matrix ,is_block=False):
        
        box = [[inf, -inf] for _ in range(3)]

        import bmesh
        cursor = bpy.context.scene.cursor.rotation_euler.to_matrix().to_4x4().inverted() 
        if self.axis == "Local":
            mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
        elif self.axis == "Cursor":
            mat =cursor @ mat
        
        bm = bmesh.from_edit_mesh(o.data)
        verts = [v for v in bm.verts if v.select] 
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
            if obj.type =='MESH' and obj.mode != 'OBJECT':#计算网格
                import bmesh
                # bm = bmesh.from_edit_mesh(o.data)
                data = obj.data
                if data.is_editmode:
                    # Gain direct access to the mesh
                    bm = bmesh.from_edit_mesh(data)
                else:
                    # Create a bmesh from mesh
                    # (won't affect mesh, unless explicitly written back)
                    bm = bmesh.new()
                    bm.from_mesh(data)

                self.objects[obj]['bound_box']['bound_box'] = self.min_max_calc(vertices = [v for v in bm.verts] , mat = mat, box = [[inf, -inf] for _ in range(3)], gtv =lambda v: v.co)
                #网格单独物体
                if obj.type == 'MESH' and bpy.context.mode == "EDIT_MESH" and get_block:
                    v_block = get_select_block(obj)
                    
                    if 'block' not in self.objects[obj]:
                        self.objects[obj]['block'] = {}
                        
                    self.objects[obj]['block'] = v_block
                    
                    if 'block' not in self.objects[obj]['bound_box']:
                        self.objects[obj]['bound_box']['block'] = {}
                        
                    for v_ in v_block:
                        verts = [v for v in bm.verts if v.index in v_block[v_]] 
                        self.objects[obj]['bound_box']['block'][str(v_)] = self.min_max_calc(verts, mat, [[inf, -inf] for _ in range(3)], lambda v: v.co)
                
                if get_whole_block:
                    
                    if 'whole_block' not in self.objects[obj]['bound_box']:
                        self.objects[obj]['bound_box']['whole_block'] = {}
                        
                    self.objects[obj]['bound_box']['whole_block'] = self.min_max_calc([v for v in bm.verts if v.select], mat, [[inf, -inf] for _ in range(3)], lambda v: v.co)
            else:#物体模式
                # def bound_box_to_xyz(o):#基本边界框
                    # return [[o.bound_box[0][_], o.bound_box[6][_]] for _ in range(3)]
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

        def new_modifder(name,obj,vg_name = None):
            

            if bpy.data.objects[name].type == 'GPENCIL':
                mod = bpy.data.objects[name].grease_pencil_modifiers.new(name=name, type="GP_LATTICE")
            else:
                mod = bpy.data.objects[name].modifiers.new(name=name, type="LATTICE")
            
            if vg_name != None:
                mod.vertex_group = vg_name
            mod.object = bpy.data.objects[obj]
        def new_lattices(name,scale,location,vgname=None):
            lt = bpy.data.lattices.new(name=name+'_LP')
            lpo = bpy.data.objects.new(name=lt.name, object_data=lt)
            bpy.context.collection.objects.link(lpo)

            if bpy.data.objects[name].type == 'MESH':
                if self.axis == "Cursor":
                    print(name,'Cursor')

                    lpo.rotation_euler = bpy.context.scene.cursor.matrix.to_euler()
                    location = bpy.context.scene.cursor.rotation_euler.to_matrix() @ Vector(location)
                
                    lpo.scale = scale
                    lpo.location = location
                
                if self.axis == "Local":
                    print(name,'Local')

                    if bpy.context.mode == 'EDIT':
                        # mat = o.rotation_euler.to_matrix().to_4x4() @ mat
                        lpo.rotation_euler = bpy.data.objects[name].rotation_euler
                        lpo.location =  bpy.data.objects[name].rotation_euler.to_matrix().to_4x4() @  location
                        # mat = bpy.data.objects[name].matrix_world
                        # mat_ = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
                        lpo.scale = scale
                        # lpo.location = location
                        
                    else:
                        lpo.rotation_euler = bpy.data.objects[name].rotation_euler
                        # lpo.location = o.rotation_euler.to_matrix().to_4x4() @ location
                        mat = bpy.data.objects[name].matrix_world
                        mat_ = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
                        lpo.scale = scale
                        lpo.location = location
                    # lpo.location = mat @ mat_.inverted() @ location
                
                # elif self.axis == "Cursor":
                #     lpo.rotation_euler = bpy.context.scene.cursor.matrix.to_euler()
                #     # lpo.location = bpy.context.scene.cursor.rotation_euler.to_matrix() @ location
                # else:
                #     lpo.location = location
                else:   #全局
                    print(name,'全局')
                    lpo.scale = scale
                    lpo.location = location
            else:   #全局
                print(name,'全局')
                lpo.scale = scale
                lpo.location = location
            
            
            
            lt.interpolation_type_u = lt.interpolation_type_v = lt.interpolation_type_w = self.lerp
            lt.points_u, lt.points_v, lt.points_w = self.res
            
            
            new_modifder(name,lt.name)

        obj_edit_mode = self.obj_edit_mode
        obj_mode = self.obj_mode



        if (obj_edit_mode  == 'whole' and context.mode == "EDIT_MESH") or (obj_mode ==  'whole' and context.mode == 'OBJECT'):
            self.box_get(selected_objects,
                        )
        else:
            for o in selected_objects:
                self.box_get(o,
                            get_block= (obj_edit_mode == 'select_block'  and context.mode == "EDIT_MESH"),
                            get_whole_block=  (obj_edit_mode == 'whole_block'  and context.mode == "EDIT_MESH"),
                            )

        return {'FINISHED'}

    def emm(self,context):
        box = [[inf, -inf] for i in range(3)]
        support_type = ["MESH", "CURVE", "FONT", "SURFACE"]

        active_object = context.active_object

        if self.action:#物体模式 and bpy.context.mode != "EDIT_MESH"
            if self.axis == "Local" and context.mode != "EDIT_MESH":
                self.axis = "Global"
            for o in bpy.context.selected_objects:
                if o.type in support_type:
                    bbox = self.box_get(o)
            print(bbox)
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
                print(bbox)
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
        if __name__ == "__ma  in__":
            from bpy.types import Panel
            layout=Panel.layout
        layout.prop(self, "axis",expand=True)
        # layout.prop(self, "mode",expand=True)
        
        if context.mode == "EDIT_MESH" :
            layout.prop(self, "obj_edit_mode",expand=True)
            layout.prop(self,'use_vert_group')
        else:
            layout.prop(self, "obj_mode",expand=True)
            
        
        layout.prop(self, "res")
        layout.prop(self, "lerp",expand=True)


if __name__ == "__main__":
    bpy.utils.register_class(Lattice_Operator)
