import bpy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .settings import scene


def load_post(dummy):
    scene_sets: 'scene.SH_Scene' = bpy.context.scene.superhive
    if len(scene_sets.metadata_update.metadata_items) != 4:
        scene_sets.metadata_update.reset()

def register():
    bpy.app.handlers.load_post.append(load_post)


def unregister():
    bpy.app.handlers.load_post.remove(load_post)