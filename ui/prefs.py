import os
from pathlib import Path

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import AddonPreferences, PropertyGroup, UILayout, UIList

from .. import __package__ as base_package
from .. import hive_mind, utils
from ..settings import scene


class SH_UL_BlenderVersions(UIList):
    def draw_item(
        self,
        context,
        layout: "UILayout",
        data,
        item: "SH_BlenderVersion",
        icon,
        active_data,
        active_propname,
        index,
        flt_flag,
    ):
        icn = "RADIOBUT_ON" if item.is_default else "RADIOBUT_OFF"
        layout.prop(item, "is_default", icon=icn, text="", emboss=False, toggle=True)

        row = layout.row()
        row.alignment = "LEFT"
        row.prop(item, "display_name", icon="BLENDER", text="", emboss=False)

        row = layout.row()
        row.active = False
        row.label(text=item.path)


class SH_BlenderVersion(PropertyGroup):
    path: StringProperty(
        name="Path",
        description="The path to the Blender executable",
        subtype="FILE_PATH",
    )

    display_name: StringProperty(
        name="Name",
        description="The name to display for the Blender version",
    )

    def _update_is_default(self, context):
        if self.is_default:
            for bv in utils.get_prefs().blender_versions:
                if bv != self:
                    bv.is_default = False

    is_default: BoolProperty(
        name="Default",
        description="Whether this Blender version is the default",
        default=False,
        update=_update_is_default,
    )

    @property
    def data(self) -> "SH_AddonPreferences":
        return utils.get_prefs()


class SH_AddonPreferences(AddonPreferences, scene.RenderThumbnailProps):
    bl_idname = base_package

    display_extras: bpy.props.BoolProperty(
        name="Display Extras",
        description="Display extra information",
        default=False,
    )

    default_author_name: StringProperty(
        name="Author Name",
        description="The name to put by default in the author field",
        default="Company Name",  # TODO: Delete this default
    )

    default_license: EnumProperty(
        name="Default License",
        description="The default license to use for new assets",
        items=hive_mind.get_licenses,
        default=2,  # TODO: Don't hardcode this
    )

    default_copyright: StringProperty(
        name="Default Copyright",
        description="The default copyright info to use for new assets",
        default="",
    )

    library_directory: StringProperty(
        name="Asset Library Directory",
        description="The directory to create new asset libraries in for the Superhive (formerly Blender Market) system",
        subtype="DIR_PATH",
        default=os.path.join(os.path.expanduser("~"), "Superhive Libraries"),
    )

    blender_versions: CollectionProperty(
        type=SH_BlenderVersion,
    )

    active_blender_version_index: IntProperty()

    non_blocking: BoolProperty(
        name="Use Separate threads for tasks (Non-Blocking)",
        default=True,
    )

    @property
    def active_blender_version(self) -> SH_BlenderVersion:
        return self.blender_versions[self.active_blender_version_index]

    @property
    def default_blender_version(self) -> SH_BlenderVersion:
        return next((bv for bv in self.blender_versions if bv.is_default), None)

    def add_blender_version(self, name: str, path: str):
        bv: SH_BlenderVersion = self.blender_versions.add()
        bv.name = name
        bv.display_name = name
        bv.path = path
        return bv

    def remove_blender_version(self, item: SH_BlenderVersion | str | int):
        if isinstance(item, int):
            self.blender_versions.remove(item)
        elif isinstance(item, str):
            bv = self.blender_versions.find(item)
            self.blender_versions.remove(bv)
        elif isinstance(item, SH_BlenderVersion):
            self.blender_versions.remove(item)

    def ensure_default_blender_version(self):
        if not self.blender_versions:
            p = Path(bpy.app.binary_path)
            bv = self.add_blender_version(p.parent.name, bpy.app.binary_path)
            bv.is_default = True
            return bv
        if not self.default_blender_version:
            self.blender_versions[0].is_default = True
            return self.blender_versions
        return self.default_blender_version

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        header, body = box.panel("quick_start", default_closed=True)
        row = header.row()
        row.scale_y = 1.25
        row.alignment = "CENTER"
        row.label(text="Quick Start Information", icon="INFO")

        if body:
            col = body.column(align=True)
            col.scale_y = 0.75
            col.label(text="Location:      Asset Browser > Side Panel > Bkeeper Tab")
            col.label(text="  " * 8 + "Ensure new dropdown on the left side of the header")
            col.label(text="  " * 8 + "is set to 'Bkeeper' instead of 'Blender'")

            layout.separator()

            col = body.column(align=True)
            col.scale_y = 0.75
            col.label(text="Add Assets to Libraries:")
            col.label(text=" " * 8 + "From Asset Browser")
            col.label(text=" " * 16 + "Select existing assets. Then right-click to bring up menu.")
            col.label(text=" " * 16 + "Notice the 'Bkeeper' section.")
            col.label(text=" " * 16 + "Click 'Add to Library'. Select library or choose '+ New'")
            col.label(text=" " * 16 + "in order to create a new library")
            col.label(text=" " * 8 + "From Outliner/3D View")
            col.label(text=" " * 16 + "Select the object(s) you want to add. Then right-click")
            col.label(text=" " * 16 + "to bring up menu. Notice the 'Bkeeper' section.")
            col.label(text=" " * 16 + "Click 'Add to Library'. Select library or choose '+ New'")
            col.label(text=" " * 16 + "to create a new library. Items will be marked as an asset and added.")

        layout.label(text="Metadata Defaults:")
        layout.prop(self, "default_author_name")
        layout.prop(self, "default_license")
        layout.prop(self, "library_directory")

        layout.separator()

        layout.label(text="Blender Versions:", icon="BLENDER")
        row = layout.row()
        row.template_list(
            "SH_UL_BlenderVersions",
            "",
            self,
            "blender_versions",
            self,
            "active_blender_version_index",
        )
        col = row.column(align=True)
        col.operator("bkeeper.add_blender_exes", icon="ADD", text="")
        col.operator("bkeeper.remove_blender_exes", icon="REMOVE", text="")
        col.operator("bkeeper.gather_blender_exes", icon="FILE_REFRESH", text="")

        layout.separator()

        row = layout.row()
        row.label(text="Thumbnail Rendering Defaults:")
        col = layout.column()
        col.use_property_decorate = False
        row = col.row()
        row.use_property_split = True
        row.prop(self, "non_blocking", text="Render in Background")

        max_width = 730
        if context.region.width > max_width:
            margin = (context.region.width - max_width) / 100
            thumbnail_row = layout.row()
            col_l = thumbnail_row.column()
            col_l.ui_units_x = margin
            col_l.separator()
            col = thumbnail_row.column()
            # col.ui_units_x = max_width
            col_r = thumbnail_row.column()
            col_r.ui_units_x = margin
            col_r.separator()
        self.draw_thumbnail_props(col)

        layout.separator()

        if self.display_extras:
            layout.label(text=f"Region Width: {context.region.width}")
        row = layout.row()
        row.alignment = "RIGHT"
        row.prop(
            self,
            "display_extras",
            emboss=False,
            text="",
            icon="UNLOCKED" if self.display_extras else "LOCKED",
        )


classes = (
    SH_UL_BlenderVersions,
    SH_BlenderVersion,
    SH_AddonPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
