import bpy
from bpy.utils import previews
from pathlib import Path


class Icons:
    def __init__(self) -> None:
        self.preview: previews.ImagePreviewCollection = previews.new()
        
        imgs_dir = Path(__file__).parent / "images"
        
        self.outdoor_harsh_icon: bpy.types.ImagePreview = None
        self.outdoor_harsh_path = imgs_dir / "outdoor_harsh.webp"

        self.outdoor_soft_icon: bpy.types.ImagePreview = None
        self.outdoor_soft_path = imgs_dir / "outdoor_soft.webp"

        self.studio_harsh_icon: bpy.types.ImagePreview = None
        self.studio_harsh_path = imgs_dir / "studio_harsh.webp"

        self.studio_soft_icon: bpy.types.ImagePreview = None
        self.studio_soft_path = imgs_dir / "studio_soft.webp"
    
    icon_names = (
        "outdoor_harsh", "outdoor_soft", "studio_harsh", "studio_soft"
    )
    
    def _load_icon(self, icon_id:str) -> None:
        path:Path = getattr(self, f"{icon_id}_path")
        if path.exists() and f"sh_{icon_id}" not in self.preview:
            setattr(
                self, f"{icon_id}_icon",
                self.preview.load(
                    f"sh_{icon_id}",
                    str(path),
                    "IMAGE"
                )
            )
    
    def register(self) -> None:
        for icon_id in self.icon_names:
            self._load_icon(icon_id)
        
    def unregister(self):
        self.preview.close()

    def reload(self):
        self.unregister()
        self.register()


sh_icons = Icons()


def register():
    sh_icons.register()


def unregister():
    sh_icons.unregister()
