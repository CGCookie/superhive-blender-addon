import bpy
from bpy.types import Operator
from bpy.props import StringProperty


class TT_OT_IconWithDescription(Operator):
    bl_idname = "bkeeper.icon_with_description"
    bl_label = ""
    bl_description = "Replace me by setting the `text` property"
    bl_options = {"REGISTER", "UNDO"}

    text: StringProperty()

    @classmethod
    def description(cls, context, properties: "TT_OT_IconWithDescription"):
        return properties.text or cls.bl_description

    def execute(self, context):
        return {"FINISHED"}


classes = (TT_OT_IconWithDescription,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
