import bpy
from bpy.types import AddonPreference


class Preference(AddonPreference):
    bl_idname = __package__
    def_res: bpy.props.IntVectorProperty(name="Default lattice resolution", default=[2, 2, 2], min=2, max=64)

    items = [('KEY_LINEAR', 'Linear', ''),
             ('KEY_CARDINAL', 'Cardinal', ''),
             ('KEY_CATMULL_ROM', 'Catmull-Rom', ''),
             ('KEY_BSPLINE', 'BSpline', '')]

    lerp: bpy.props.EnumProperty(name="Interpolation", items=items, default='KEY_LINEAR')

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "def_res")
        layout.prop(self, "lerp")


def register():
    bpy.utils.register_class(Preference)


def unregister():
    bpy.utils.unregister_class(Preference)
