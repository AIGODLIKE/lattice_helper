import bpy


def get_pref():
    return bpy.context.preferences.addons[__package__].preferences
