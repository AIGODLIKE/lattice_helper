import bpy
from mathutils import Matrix, Vector
from math import inf
from time import time

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader

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
    import bmesh
    me = obj.data
    if me.is_editmode:
        # Gain direct access to the mesh
        bm = bmesh.from_edit_mesh(me)
    else:
        # Create a bmesh from mesh
        # (won't affect mesh, unless explicitly written back)
        bm = bmesh.new()
        bm.from_mesh(me)
    bm.verts.ensure_lookup_table()   
    bm.edges.ensure_lookup_table()   
    bm.faces.ensure_lookup_table()

    verts = []
    for vert in bm.verts:
        if vert.select:
            verts.append(vert)

    # edges = []
    # for edge in bm.edges:
    #     if edge.select:
    #         edges.append(edge)

    # faces = []
    # for face in bm.faces:
    #     if face.select:
    #         faces.append(face)



    block_list = {}
    # select_verts_index = [v.index for v in verts]#所有选择的顶点
    

    
    if len(verts) <= 4:#没有选中就反回整个网格
        return {0:[vert.index for vert in bm.verts]}#
    else:
        # print(tmp_verts)
        
        def while_list(tmp_verts):
            
            tmp_: list =[]
            for_list = []
            for_list.append(tmp_verts)
            tmp_.append(tmp_verts)
            
            while len(for_list) != 0:
                # print(for_list)
            
                def get_list(for_list):
                    list_ = []
                    for bmVert in for_list:
                        for link_edge in bmVert.link_edges:
                            for v in link_edge.verts:
                                if v != bmVert and v.select and v not in tmp_:
                                    tmp_.append(v)
                                    list_.append(v)
                                    # print("v",v)
                        # tmp_.remove(bmVert)
                    return list_
                for_list = get_list(for_list)
            return tmp_

        B = verts[0]

        while len(verts) != 0:
            A = while_list(B)
            block_list[str(B.index)] = [i.index for i in A]
            # print(len(verts))
            verts= list(set(verts) - set(A))
            # print(len(verts),len(A),verts[-1])   
            # print(len(verts))
            if len(verts) != 0:
                B = verts[0]
            
        del bm
        return block_list
    
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
    items_ = [
        ('whole', '整体', '所有选择物体作为一个整体'),  #物体模式，所有选择作为一个整体， 编辑模式也是所有选择的内容作为一个整体
        ('bound_box', '边界框', '以每一个选择物体的边界框作为一个单独的晶格'),
        # ('individual', '各自', '每一个选择的物体作为一个单独的晶格'),
        ('select_block', '选择块(编辑模式)', '将编辑模式内每一个选择的块作为单独的一个区域添加一个晶格'),        
        ('whole_block', '整个块(编辑模式)', '将编辑模式内所有选择的块作为一个区域添加晶格'),
             ]
    
    mode: bpy.props.EnumProperty(default='bound_box',name="模式", items=items_)

    def __init__(self) -> None:
        # self.res[:] = bpy.context.preferences.addons[__package__].preferences.def_res
        # self.lerp = bpy.context.preferences.addons[__package__].preferences.lerp
        # self.data = {}
        
        # if bpy.context.mode == "EDIT_MESH":
        #     self.action=True
        pass


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
        v_block = get_select_block(o)


        for v_ in v_block:
            verts = [v for v in bm.verts if v.index in v_block[v_]] 
            

            E = self.min_max_calc(verts, mat, box, lambda v: v.co)
            if o.name not in self.data:
                self.data[o.name] = {}
            self.data[o.name][str(v_)] = E


    def box_get(self, o: bpy.types.Object):
        mat = o.matrix_world
        name = o.name
        
        
        
        cursor = bpy.context.scene.cursor.rotation_euler.to_matrix().to_4x4().inverted() 
        
        
        if self.axis == "Local":
            
            if o.mode == 'EDIT':
                # mat = o.rotation_euler.to_matrix().to_4x4() @ mat

                mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()
            else:
                mat = Matrix.Translation(mat.to_translation()) @ Matrix.Diagonal(mat.to_scale()).to_4x4()

            
        elif self.axis == "Cursor":
            mat = cursor @ mat

        if name  not in self.data:
            self.data[name] = {}
            
            
        
        if o.type =='MESH':
            import bmesh
            
            # bm = bmesh.from_edit_mesh(o.data)
            data = o.data
            if data.is_editmode:
                # Gain direct access to the mesh
                bm = bmesh.from_edit_mesh(data)
            else:
                # Create a bmesh from mesh
                # (won't affect mesh, unless explicitly written back)
                bm = bmesh.new()
                bm.from_mesh(data)
                
            
            self.data[name]['bound_box'] = self.min_max_calc(vertices = [v for v in bm.verts] , mat = mat, box = [[inf, -inf] for _ in range(3)], gtv =lambda v: v.co)
            #网格单独物体
            if o.type == 'MESH' and bpy.context.mode == "EDIT_MESH":
                v_block = get_select_block(o)


                for v_ in v_block:
                    verts = [v for v in bm.verts if v.index in v_block[v_]] 
                
                    if name not in self.data:
                        self.data[name] = {}
                    self.data[name][str(v_)] = self.min_max_calc(verts, mat, [[inf, -inf] for _ in range(3)], lambda v: v.co)
                self.data[name]['whole_block'] = self.min_max_calc([v for v in bm.verts if v.select], mat, [[inf, -inf] for _ in range(3)], lambda v: v.co)
        else:
            def bound_box_to_xyz(o):#基本边界框
                return [[o.bound_box[0][_], o.bound_box[6][_]] for _ in range(3)]
            self.data[name]['bound_box'] = bound_box_to_xyz(o)
        
        
        
        return self.data[name]
        
        
        
        # box = [[inf, -inf] for _ in range(3)]
        
        # mat = o.matrix_world
        
        # def add_box(box):
        #     # print('add_box',box)
        #     if o.name not in self.data:
        #         self.data[o.name] = {}
        #     if o.name not in self.data[o.name]:
        #         self.data[o.name][o.name] = box
                
        #     # {}
        #     # if o.name not in self.data[o.name][o.type]:
        #     #     self.data[o.name][o.type][o.name]= box
        #     else:
        #         return self.data[o.name][o.name]#[o.name]

        
        # if bpy.context.mode == 'EDIT_MESH':
        #     print('bpy.context.mode == "EDIT_MESH"')
        #     self.box_get_bmesh(o, box, mat,is_block=True)
        #     return self.data[o.name]

        #     # def bound_box_to_xyz(o):
        #     #     return [[o.bound_box[0][_], o.bound_box[6][_]] for _ in range(3)]
        #     # box = bound_box_to_xyz(o)
        #     # # print('_____bound_box_to_xyz',box)
        #     # # me = o.data.copy()
        #     # # obj = bpy.data.objects.new(name=me.name, object_data=me)
        #     # # bpy.context.collection.objects.link(obj)
        #     # # obj.matrix_world = mat
        #     # # self.box_get_common(obj, box, mat)
        #     # # bpy.data.objects.remove(obj)
        #     # add_box(box)
            
        # elif o.type != "MESH":
        #     print('o.type != "MESH"')
        #     to_translation = o.matrix_world.to_translation()
        #     bound_box = o.bound_box
        #     # print(bound_box)
        # #     self.box_get_common(o, box, mat)

        # #     add_box(box)
        # #     # return box
        # # # print('data',self.data)
        # #     return self.data[o.name]
        #     # print(bound_box)
            
        #     # for b in  bound_box:
        #     #     b = list(b)
        #     #     for i in b:
        #     #         # print(i,b.index(i))
        #     #         print(b)

                
            
        #     # bound_box = [[b + to_translation[_] for b in  o.bound_box for j in b  for _ in range(3)]]


        #     def bound_box_to_xyz(o):
        #         return [[bound_box[0][_], bound_box[6][_]] for _ in range(3)]
            
        #     box = bound_box_to_xyz(o)
        #     # return self.data[o.name]
        #     # # print('_____bound_box_to_xyz',box)
        #     # # me = o.data.copy()
        #     # # obj = bpy.data.objects.new(name=me.name, object_data=me)
        #     # # bpy.context.collection.objects.link(obj)
        #     # # obj.matrix_world = mat
        #     # # self.box_get_common(obj, box, mat)
        #     # # bpy.data.objects.remove(obj)
            
        #     # add_box(box)
            
        #     # # return box
        #     # return self.data[o.name]

        # elif o.type == "MESH":
        #     print('o.type == "MESH"')
        #     self.box_get_common(o, box, mat)
            
        #     add_box(box)


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
        print('execute')
        # self.invoke
        self.EMMM(context)
        context.area.header_text_set(None)

        return {'FINISHED'}

    def invoke(self, context, event):
        print('invoke')
        args = (self, context)

        self._handle = []

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    # {物体:边界框数据，物体:边界框数据}
    def modal(self, context, event):
                
        # if o.type not in support_type:
        #     self.report({"ERROR"}, f"物体{o.name}类型:{o.type}不支持！")
        #     return {"FINISHED"}

        print(f'modal____________________________{event.value}______________________{event.type}')
        # print('____________')
        if event.type == "ESC" and event.value == "PRESS" or event.type == "RIGHTMOUSE" and event.value == "PRESS":#退出
            context.window.cursor_set("DEFAULT")
            context.area.header_text_set(None)
            for i in self._handle:
                bpy.types.SpaceView3D.draw_handler_remove(i, 'WINDOW')
            context.area.tag_redraw()

            return {'CANCELLED'}
        
        elif event.type == "RET" and event.value == "PRESS" or  event.type == "LEFTMOUSE" and event.value == "PRESS":#确认
            context.window.cursor_set("DEFAULT")
            context.area.header_text_set(None)
            for i in self._handle:
                bpy.types.SpaceView3D.draw_handler_remove(i, 'WINDOW')
            context.area.tag_redraw()

            return {'FINISHED'}
        else:
            self.EMMM(context)
            return {'RUNNING_MODAL'}

    def EMMM(self,context):
        support_type = ['LATTICE',"MESH", "CURVE", "FONT", "SURFACE","HAIR","GPENCIL"]
        active_object = context.active_object#实例当前活动物体出来备用
        context.area.tag_redraw()

        #         box = [[inf, -inf] for _ in range(3)]
        #data = {
            # name:{
                # name:[边界框[*2]*3],      获取基本边界框
                # VN:[边界框[*2]*3]     如果在编辑模式就可以添加很多的分块
                # 网格所选整体边界框
                # }
            
            # }

        self.data = {}
    
        selected_objects =  [obj for obj in context.selected_objects if obj.type in support_type] \
                                if context.mode == 'OBJECT' else \
                            [obj for obj in context.selected_objects if obj.type == 'MESH' and context.mode =='EDIT_MESH']
                            #get所有可用物体列表,如果在网格编辑模式则只获取网格的
                            
                        
        if len(selected_objects) == 0 :
            self.report({"ERROR"}, f"未选择可添加晶格物体!!")
            return {"FINISHED"}

        # if self.axis == "Local" and context.mode == "EDIT_MESH":
        #     self.axis = "Global"
        
        for o in selected_objects:
            
            #get基于原点的边界框，添加晶格时再添加缩放和旋转信息
            #通过
            
            bbox = self.box_get(o)
        
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
            
            mod = bpy.data.objects[name].modifiers.new(name=name, type="LATTICE")
            
            if vg_name != None:
                mod.vertex_group = vg_name
            mod.object = bpy.data.objects[obj]

        def new_lattices(name,scale,location,vgname=None):
            lt = bpy.data.lattices.new(name=name+'_LP')
            lpo = bpy.data.objects.new(name=lt.name, object_data=lt)
            bpy.context.collection.objects.link(lpo)

            if self.axis == "Cursor":
                lpo.rotation_euler = bpy.context.scene.cursor.matrix.to_euler()
                location = bpy.context.scene.cursor.rotation_euler.to_matrix() @ Vector(location)
            
                lpo.scale = scale
                lpo.location = location
                
            if self.axis == "Local":
                
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
            else:
                lpo.scale = scale
                lpo.location = location
            
            lt.interpolation_type_u = lt.interpolation_type_v = lt.interpolation_type_w = self.lerp
            lt.points_u, lt.points_v, lt.points_w = self.res
            
            
            new_modifder(name,lt.name)

        
        
        
        tmp_add_list = {}        
        mode = self.mode
        for obj_ in self.data:
            obj = self.data[obj_]
            for bo in obj:
                box = obj[bo]
                print(obj_,bo,box)
                scale = [(b[1] - b[0]) if abs(b[1] - b[0]) > 0.00000001 else 0.15 for b in box]
                location = [(b[1] + b[0]) / 2 for b in box]
                
                if mode  == 'whole':
                    
                    # if 'whole' not in tmp_add_list:
                    #     tmp_add_list['whole']=calc(bo,bo)
                    # else:
                    #     tmp_add_list['whole']=calc(tmp_add_list['whole'],bo)
                    pass

                elif mode == 'bound_box':
                    if bo == 'bound_box':
                        new_lattices(obj_,scale,location)
                elif mode == 'select_block':
                    
                    if bo not in  ('bound_box','whole_block'):
                        new_lattices(obj_,scale,location)


                elif mode == 'whole_block':
                    if bo == 'whole_block':
                        new_lattices(obj_,scale,location)            
                else:pass
                    
                    
                    # for i in self.data:
                        # print(i,':',self.data[i])

        # for j in tmp_add_list:
        #     EMM = bpy.types.SpaceView3D.draw_handler_add(draw_3d(self,tmp_add_list[j]), (), 'WINDOW', 'POST_VIEW')
        #     self._handle.append(EMM)
            
            
        # print(bbox)

        # print(o,scale,location,self.data[o.name])


        objs = [obje.name for obje in selected_objects]
        context.area.header_text_set(f"当前所选物体 {len(objs)} {list(objs)}")
        print(self.data)
        print(tmp_add_list)
        return {'RUNNING_MODAL'}

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
        if __name__ == "__ma  in__":
            from bpy.types import Panel
            layout=Panel.layout
        layout.prop(self, "axis",expand=True)
        layout.prop(self, "mode",expand=True)
        # if context.mode != "EDIT_MESH" :
        #     layout.prop(self, "action")
        
        layout.prop(self, "set_parent")
        
        # if context.mode == "EDIT_MESH"  and len(context.selected_objects)>=2 :
        #     layout.prop(self, "set_selected_objects_is_active_parent")
        
        layout.prop(self, "res")
        layout.prop(self, "lerp",expand=True)


if __name__ == "__main__":
    bpy.utils.register_class(Lattice_Operator)
    # bpy.utils.register_class(AddonPreference)

# from mathutils import Vector
# ob = C.object
# bbox_corners = [Vector(corner) for corner in ob.bound_box]
# # bbox_corners = [ob.matrix_world @ Vector(corner) for corner in ob.bound_box]  # Use this in V2.80+
# bbox_corners

# o = C.object
# box = [[o.bound_box[0][_], o.bound_box[6][_]] for _ in range(3)]
# box