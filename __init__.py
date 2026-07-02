bl_info = {
    "name": "BudsCollab for Blender",
    "author": "BudsCollab",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BudsCollab",
    "description": "Create, validate, and send Blender assets through BudsCollab.",
    "category": "Import-Export",
}

import bpy


class BudsCollabBridgeSettings(bpy.types.PropertyGroup):
    space_id: bpy.props.StringProperty(name="Space", default="Select a space")
    room_id: bpy.props.StringProperty(name="Room", default="Select a room")
    status: bpy.props.StringProperty(name="Status", default="Not logged in")


class BUDSCOLLAB_OT_login(bpy.types.Operator):
    bl_idname = "budscollab.login"
    bl_label = "Login"

    def execute(self, context):
        context.scene.budscollab_bridge.status = "Connected"
        self.report({"INFO"}, "BudsCollab login placeholder")
        return {"FINISHED"}


class BUDSCOLLAB_OT_validate_selection(bpy.types.Operator):
    bl_idname = "budscollab.validate_selection"
    bl_label = "Validate Selection"

    def execute(self, context):
        context.scene.budscollab_bridge.status = "Ready to upload"
        self.report({"INFO"}, "Validation placeholder: selection is ready")
        return {"FINISHED"}


class BUDSCOLLAB_OT_upload_selection(bpy.types.Operator):
    bl_idname = "budscollab.upload_selection"
    bl_label = "Upload Selected"

    def execute(self, context):
        context.scene.budscollab_bridge.status = "Upload queued"
        self.report({"INFO"}, "Upload selected placeholder")
        return {"FINISHED"}


class BUDSCOLLAB_OT_open_preview(bpy.types.Operator):
    bl_idname = "budscollab.open_preview"
    bl_label = "Open Web Preview"

    def execute(self, context):
        bpy.ops.wm.url_open(url="https://app.budscollab.com/preview/3d")
        return {"FINISHED"}


class BUDSCOLLAB_PT_bridge_panel(bpy.types.Panel):
    bl_label = "BudsCollab"
    bl_idname = "BUDSCOLLAB_PT_bridge_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BudsCollab"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.budscollab_bridge

        layout.label(text="BudsCollab for Blender")
        layout.prop(settings, "status")
        layout.operator("budscollab.login")

        layout.separator()
        layout.prop(settings, "space_id")
        layout.prop(settings, "room_id")

        layout.separator()
        layout.operator("budscollab.validate_selection")
        layout.operator("budscollab.upload_selection")
        layout.operator("budscollab.open_preview")

        layout.separator()
        layout.label(text="Import from BudsCollab")
        layout.label(text="Send/open in Unity later")


CLASSES = (
    BudsCollabBridgeSettings,
    BUDSCOLLAB_OT_login,
    BUDSCOLLAB_OT_validate_selection,
    BUDSCOLLAB_OT_upload_selection,
    BUDSCOLLAB_OT_open_preview,
    BUDSCOLLAB_PT_bridge_panel,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.budscollab_bridge = bpy.props.PointerProperty(type=BudsCollabBridgeSettings)


def unregister():
    del bpy.types.Scene.budscollab_bridge
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
