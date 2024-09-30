from typing import TYPE_CHECKING

import bpy

if TYPE_CHECKING:
    from .settings import scene


def load_post(dummy):
    scene_sets: "scene.SH_Scene" = bpy.context.scene.superhive
    if len(scene_sets.metadata_update.metadata_items) != 4:
        scene_sets.metadata_update.reset()


def register():
    bpy.app.handlers.load_post.append(load_post)


def unregister():
    if load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post)
