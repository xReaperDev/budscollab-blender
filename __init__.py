bl_info = {
    "name": "BudsCollab for Blender",
    "author": "BudsCollab",
    "version": (0, 1, 4),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BudsCollab",
    "description": "Connect Blender to BudsCollab spaces and prepare GLB assets.",
    "category": "Import-Export",
}

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import bpy

WORKSPACE_ENDPOINT = "/api/creator-tools/workspace"
NONE_ID = "__none__"
TARGET_PROFILES = {
    "room_object": {
        "label": "Room object",
        "good_triangles": 70000,
        "max_triangles": 250000,
        "good_materials": 8,
        "max_materials": 32,
        "max_bounds": 6.0,
    },
    "mobile_light": {
        "label": "Mobile / lightweight",
        "good_triangles": 20000,
        "max_triangles": 70000,
        "good_materials": 4,
        "max_materials": 12,
        "max_bounds": 4.0,
    },
    "high_detail": {
        "label": "High detail",
        "good_triangles": 250000,
        "max_triangles": 1000000,
        "good_materials": 16,
        "max_materials": 64,
        "max_bounds": 12.0,
    },
    "print_cleanup": {
        "label": "Print cleanup",
        "good_triangles": 150000,
        "max_triangles": 500000,
        "good_materials": 4,
        "max_materials": 16,
        "max_bounds": 0.5,
    },
}
TARGET_PROFILE_ITEMS = tuple(
    (profile_id, config["label"], profile_id)
    for profile_id, config in TARGET_PROFILES.items()
)


def _settings(context):
    return context.scene.budscollab_bridge


def _space_items(self, context):
    settings = _settings(context)
    if len(settings.spaces) == 0:
        return [(NONE_ID, "Connect to load spaces", "Paste a token and refresh spaces")]
    return [
        (space.space_id, f"{space.name} ({space.role})", space.space_id)
        for space in settings.spaces
    ]


def _room_items(self, context):
    settings = _settings(context)
    rooms = [
        room
        for room in settings.rooms
        if room.space_id == settings.selected_space_id
    ]
    if len(rooms) == 0:
        return [(NONE_ID, "No rooms loaded", "Refresh spaces after selecting a valid token")]
    return [
        (room.room_id, f"{room.emoji} {room.name}".strip(), room.room_id)
        for room in rooms
    ]


def _selected_space_updated(self, context):
    settings = _settings(context)
    rooms = [
        room
        for room in settings.rooms
        if room.space_id == settings.selected_space_id
    ]
    settings.selected_room_id = rooms[0].room_id if rooms else NONE_ID


def _normalize_api_base(value):
    trimmed = value.strip().rstrip("/")
    return trimmed or "https://app.budscollab.com"


def _workspace_url(api_base):
    return f"{_normalize_api_base(api_base)}{WORKSPACE_ENDPOINT}"


def _request_workspace(api_base, access_token):
    request = urllib.request.Request(
        _workspace_url(api_base),
        headers={
            "Authorization": f"Bearer {access_token.strip()}",
            "Accept": "application/json",
            "User-Agent": "BudsCollab-Blender/0.1.4",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {detail[:240]}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Network error: {error.reason}") from error

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as error:
        raise RuntimeError("BudsCollab returned non-JSON workspace data") from error
    if not isinstance(parsed, dict) or parsed.get("ok") is not True:
        message = parsed.get("error") if isinstance(parsed, dict) else "invalid_response"
        raise RuntimeError(f"BudsCollab rejected the Creator Tools token: {message}")
    spaces = parsed.get("spaces")
    if not isinstance(spaces, list):
        raise RuntimeError("BudsCollab workspace response is missing spaces")
    return spaces


def _as_text(value, fallback=""):
    return value if isinstance(value, str) and value else fallback


def _selected_meshes(context):
    return [obj for obj in context.selected_objects if obj.type == "MESH"]


def _active_profile(settings):
    return TARGET_PROFILES.get(settings.target_profile, TARGET_PROFILES["room_object"])


def _collect_asset_report(context):
    settings = _settings(context)
    profile = _active_profile(settings)
    meshes = _selected_meshes(context)
    if len(meshes) == 0:
        return False, "Select one or more mesh objects before checking the asset."

    vertex_count = 0
    triangle_count = 0
    material_slots = 0
    largest_dimension = 0.0
    missing_materials = []
    for obj in meshes:
        mesh = obj.data
        vertex_count += len(mesh.vertices)
        triangle_count += sum(max(len(poly.vertices) - 2, 1) for poly in mesh.polygons)
        material_slots += len(obj.material_slots)
        largest_dimension = max(largest_dimension, max(obj.dimensions))
        if len(obj.material_slots) == 0:
            missing_materials.append(obj.name)

    warnings = []
    notes = []
    if vertex_count == 0 or triangle_count == 0:
        warnings.append("no renderable geometry")
    if triangle_count > profile["max_triangles"]:
        warnings.append("very high triangle count")
    elif triangle_count > profile["good_triangles"]:
        notes.append("triangle count above lightweight target")
    if material_slots > profile["max_materials"]:
        warnings.append("too many material slots")
    elif material_slots > profile["good_materials"]:
        notes.append("material slots above lightweight target")
    if largest_dimension > profile["max_bounds"]:
        warnings.append("large object bounds")
    if missing_materials:
        warnings.append(f"{len(missing_materials)} mesh object(s) without materials")

    readiness = "Good" if not warnings and not notes else "Review" if not warnings else "Needs fixes"
    status = (
        f"{readiness} for {profile['label']}: {len(meshes)} mesh object(s), {vertex_count:,} vertices, "
        f"{triangle_count:,} triangles, {material_slots} material slot(s), "
        f"{largest_dimension:.1f}m max bounds"
    )
    if warnings:
        return False, f"{status}. Check: {', '.join(warnings)}."
    if notes:
        return True, f"{status}. Optimize: {', '.join(notes)}."
    return True, f"{status}. Ready to export as GLB."


def _room_by_id(settings, room_id):
    for room in settings.rooms:
        if room.room_id == room_id:
            return room
    return None


class BudsCollabSpaceItem(bpy.types.PropertyGroup):
    space_id: bpy.props.StringProperty(name="Space ID")
    name: bpy.props.StringProperty(name="Name")
    role: bpy.props.StringProperty(name="Role", default="viewer")
    open_url: bpy.props.StringProperty(name="Open URL")


class BudsCollabRoomItem(bpy.types.PropertyGroup):
    room_id: bpy.props.StringProperty(name="Room ID")
    space_id: bpy.props.StringProperty(name="Space ID")
    name: bpy.props.StringProperty(name="Name")
    emoji: bpy.props.StringProperty(name="Emoji")
    open_url: bpy.props.StringProperty(name="Open URL")


class BudsCollabBridgeSettings(bpy.types.PropertyGroup):
    api_base_url: bpy.props.StringProperty(
        name="BudsCollab URL",
        default="https://app.budscollab.com",
    )
    access_token: bpy.props.StringProperty(
        name="Creator Tools Token",
        subtype="PASSWORD",
        description="BudsCollab Creator Tools token for loading your spaces and rooms",
    )
    status: bpy.props.StringProperty(name="Status", default="Not connected")
    spaces: bpy.props.CollectionProperty(type=BudsCollabSpaceItem)
    rooms: bpy.props.CollectionProperty(type=BudsCollabRoomItem)
    selected_space_id: bpy.props.EnumProperty(
        name="Space",
        items=_space_items,
        update=_selected_space_updated,
    )
    selected_room_id: bpy.props.EnumProperty(name="Room", items=_room_items)
    validation_summary: bpy.props.StringProperty(
        name="Asset Check",
        default="No asset checked",
    )
    target_profile: bpy.props.EnumProperty(
        name="Target",
        items=TARGET_PROFILE_ITEMS,
        default="room_object",
        description="Validation target for this export",
    )
    export_path: bpy.props.StringProperty(
        name="GLB Export Path",
        subtype="FILE_PATH",
        default="//budscollab-export.glb",
    )


class BUDSCOLLAB_OT_open_login(bpy.types.Operator):
    bl_idname = "budscollab.open_login"
    bl_label = "Open BudsCollab Login"

    def execute(self, context):
        settings = _settings(context)
        bpy.ops.wm.url_open(
            url=f"{_normalize_api_base(settings.api_base_url)}/sign-in"
        )
        return {"FINISHED"}


class BUDSCOLLAB_OT_refresh_workspace(bpy.types.Operator):
    bl_idname = "budscollab.refresh_workspace"
    bl_label = "Connect and Load Spaces"

    def execute(self, context):
        settings = _settings(context)
        if not settings.access_token.strip():
            settings.status = "Access token required"
            self.report({"ERROR"}, "Paste a BudsCollab Creator Tools token first.")
            return {"CANCELLED"}

        try:
            spaces_payload = _request_workspace(
                settings.api_base_url,
                settings.access_token,
            )
        except RuntimeError as error:
            settings.status = "Connection failed"
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        settings.spaces.clear()
        settings.rooms.clear()
        first_space_id = ""
        first_room_id = ""
        room_count = 0

        for space_payload in spaces_payload:
            if not isinstance(space_payload, dict):
                continue
            space_id = _as_text(space_payload.get("spaceId"))
            name = _as_text(space_payload.get("name"), space_id)
            if not space_id:
                continue
            if not first_space_id:
                first_space_id = space_id
            space = settings.spaces.add()
            space.space_id = space_id
            space.name = name
            space.role = _as_text(space_payload.get("role"), "viewer")
            space.open_url = _as_text(space_payload.get("openUrl"))

            rooms_payload = space_payload.get("rooms")
            if not isinstance(rooms_payload, list):
                continue
            for room_payload in rooms_payload:
                if not isinstance(room_payload, dict):
                    continue
                room_id = _as_text(room_payload.get("roomId"))
                room_name = _as_text(room_payload.get("name"), room_id)
                if not room_id:
                    continue
                room = settings.rooms.add()
                room.room_id = room_id
                room.space_id = space_id
                room.name = room_name
                room.emoji = _as_text(room_payload.get("emoji"))
                room.open_url = _as_text(room_payload.get("openUrl"))
                room_count += 1
                if not first_room_id:
                    first_room_id = room_id

        settings.selected_space_id = first_space_id or NONE_ID
        settings.selected_room_id = first_room_id or NONE_ID
        settings.status = f"Loaded {len(settings.spaces)} space(s), {room_count} room(s)"
        return {"FINISHED"}


class BUDSCOLLAB_OT_check_selection(bpy.types.Operator):
    bl_idname = "budscollab.check_selection"
    bl_label = "Check Selected Asset"

    def execute(self, context):
        ok, summary = _collect_asset_report(context)
        settings = _settings(context)
        settings.validation_summary = summary
        settings.status = "Asset check passed" if ok else "Asset check needs attention"
        self.report({"INFO"} if ok else {"WARNING"}, summary)
        return {"FINISHED"}


class BUDSCOLLAB_OT_export_selection(bpy.types.Operator):
    bl_idname = "budscollab.export_selection"
    bl_label = "Export Selected GLB"

    def execute(self, context):
        settings = _settings(context)
        ok, summary = _collect_asset_report(context)
        settings.validation_summary = summary
        if not ok:
            settings.status = "Fix asset check before export"
            self.report({"ERROR"}, summary)
            return {"CANCELLED"}

        export_path = bpy.path.abspath(settings.export_path)
        if not export_path.lower().endswith(".glb"):
            export_path = f"{export_path}.glb"
        Path(os.path.dirname(export_path)).mkdir(parents=True, exist_ok=True)

        try:
            bpy.ops.export_scene.gltf(
                filepath=export_path,
                export_format="GLB",
                use_selection=True,
            )
        except Exception as error:
            settings.status = "GLB export failed"
            self.report({"ERROR"}, f"GLB export failed: {error}")
            return {"CANCELLED"}

        settings.export_path = export_path
        settings.status = f"Exported {os.path.basename(export_path)}"
        self.report({"INFO"}, f"Exported GLB: {export_path}")
        return {"FINISHED"}


class BUDSCOLLAB_OT_prepare_selection(bpy.types.Operator):
    bl_idname = "budscollab.prepare_selection"
    bl_label = "Prepare Selected Meshes"

    def execute(self, context):
        meshes = _selected_meshes(context)
        settings = _settings(context)
        if len(meshes) == 0:
            settings.status = "Select mesh objects first"
            self.report({"ERROR"}, "Select one or more mesh objects before preparing.")
            return {"CANCELLED"}

        original_active = context.view_layer.objects.active
        original_selected = list(context.selected_objects)
        prepared = 0
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass

        for obj in meshes:
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            context.view_layer.objects.active = obj
            try:
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.mesh.normals_make_consistent(inside=False)
                bpy.ops.object.mode_set(mode="OBJECT")
                prepared += 1
            except Exception as error:
                settings.status = "Prepare selected failed"
                self.report({"ERROR"}, f"Could not prepare {obj.name}: {error}")
                return {"CANCELLED"}
        bpy.ops.object.select_all(action="DESELECT")
        for obj in original_selected:
            obj.select_set(True)
        context.view_layer.objects.active = original_active

        ok, summary = _collect_asset_report(context)
        settings.validation_summary = summary
        settings.status = f"Prepared {prepared} mesh object(s)"
        self.report({"INFO"} if ok else {"WARNING"}, settings.status)
        return {"FINISHED"}


class BUDSCOLLAB_OT_open_room(bpy.types.Operator):
    bl_idname = "budscollab.open_room"
    bl_label = "Open Selected Room"

    def execute(self, context):
        settings = _settings(context)
        room = _room_by_id(settings, settings.selected_room_id)
        if room is None or not room.open_url:
            settings.status = "Select a loaded room first"
            self.report({"ERROR"}, "Refresh spaces and select a BudsCollab room.")
            return {"CANCELLED"}
        bpy.ops.wm.url_open(url=room.open_url)
        settings.status = f"Opened {room.name}"
        return {"FINISHED"}


class BUDSCOLLAB_PT_bridge_panel(bpy.types.Panel):
    bl_label = "BudsCollab"
    bl_idname = "BUDSCOLLAB_PT_bridge_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BudsCollab"

    def draw(self, context):
        layout = self.layout
        settings = _settings(context)

        connection = layout.box()
        connection.label(text="Connection")
        connection.label(text=f"Status: {settings.status}")
        connection.prop(settings, "api_base_url")
        connection.prop(settings, "access_token")
        connection.operator("budscollab.open_login")
        connection.operator("budscollab.refresh_workspace")

        destination = layout.box()
        destination.label(text="Destination")
        destination.prop(settings, "selected_space_id")
        destination.prop(settings, "selected_room_id")
        open_room = destination.row()
        open_room.enabled = len(settings.rooms) > 0
        open_room.operator("budscollab.open_room")

        asset = layout.box()
        asset.label(text="Asset")
        asset.prop(settings, "target_profile")
        asset.label(text=settings.validation_summary)
        asset.operator("budscollab.check_selection")
        asset.operator("budscollab.prepare_selection")
        asset.prop(settings, "export_path")
        asset.operator("budscollab.export_selection")


CLASSES = (
    BudsCollabSpaceItem,
    BudsCollabRoomItem,
    BudsCollabBridgeSettings,
    BUDSCOLLAB_OT_open_login,
    BUDSCOLLAB_OT_refresh_workspace,
    BUDSCOLLAB_OT_check_selection,
    BUDSCOLLAB_OT_export_selection,
    BUDSCOLLAB_OT_prepare_selection,
    BUDSCOLLAB_OT_open_room,
    BUDSCOLLAB_PT_bridge_panel,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.budscollab_bridge = bpy.props.PointerProperty(
        type=BudsCollabBridgeSettings
    )


def unregister():
    del bpy.types.Scene.budscollab_bridge
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
