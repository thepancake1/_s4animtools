import json
import bpy
from bpy.props import IntProperty, CollectionProperty, FloatProperty
from bpy.types import PropertyGroup

class AnimationEvent(PropertyGroup):
    info: bpy.props.StringProperty()


class SoundEventInfo(PropertyGroup):
    @property
    def info(self):
        return json.dumps({"frame_number" : self.frame_number, "sound_name" : self.sound_name})

    @info.setter
    def info(self, value):
        try:
            value = json.loads(value)

            self.frame_number = value["frame_number"]
            self.sound_name = value["sound_name"]
        except json.decoder.JSONDecodeError:
            pass
    frame_number : bpy.props.IntProperty()
    sound_name : bpy.props.StringProperty()


class SnapEventInfo(PropertyGroup):
    @property
    def info(self):
        return json.dumps({"frame_number" : self.frame_number, "target_actor" : self.target_actor, "target_bone" : self.target_bone})

    @info.setter
    def info(self, value):
        try:
            value = json.loads(value)

            self.frame_number = value["frame_number"]
            self.target_actor = value["target_actor"]
            self.target_bone = value["target_bone"]
        except json.decoder.JSONDecodeError:
            pass
    frame_number : bpy.props.IntProperty()
    target_actor : bpy.props.StringProperty()
    target_bone : bpy.props.StringProperty()


class ScriptEventInfo(PropertyGroup):
    @property
    def info(self):
        return json.dumps({"frame_number" : self.frame_number, "event_id" : self.event_id})

    @info.setter
    def info(self, value):
        try:
            value = json.loads(value)

            self.frame_number = value["frame_number"]
            self.event_id = value["event_id"]
        except json.decoder.JSONDecodeError:
            pass
    frame_number : bpy.props.IntProperty()
    event_id : bpy.props.IntProperty()


class ParentEventInfo(PropertyGroup):
    @property
    def info(self):
        return json.dumps({"frame_number" : self.frame_number, "child_actor" : self.child_actor,
                           "parent_actor" : self.parent_actor, "parent_bone" : self.parent_bone})

    @info.setter
    def info(self, value):
        try:
            value = json.loads(value)

            self.frame_number = value["frame_number"]
            self.child_actor = value["child_actor"]
            self.parent_actor = value["parent_actor"]
            self.parent_bone = value["parent_bone"]

        except json.decoder.JSONDecodeError:
            pass
    frame_number : bpy.props.IntProperty()
    child_actor : bpy.props.StringProperty()
    parent_actor : bpy.props.StringProperty()
    parent_bone : bpy.props.StringProperty()


class VisibilityEventInfo(PropertyGroup):
    @property
    def info(self):
        return json.dumps({"frame_number" : self.frame_number, "actor" : self.actor, "visibility" : self.visibility})

    @info.setter
    def info(self, value):
        try:
            value = json.loads(value)

            self.frame_number = value["frame_number"]
            self.actor = value["actor"]
            self.visibility = value["visibility"]
        except json.decoder.JSONDecodeError:
            pass
    frame_number : bpy.props.IntProperty()
    actor : bpy.props.StringProperty()
    visibility : bpy.props.BoolProperty()



class ReactionEventInfo(PropertyGroup):
    @property
    def info(self):
        return json.dumps({"frame_number" : self.frame_number, "reaction_asm" : self.reaction_asm, "reaction_state" : self.reaction_state})

    @info.setter
    def info(self, value):
        try:
            value = json.loads(value)

            self.frame_number = value["frame_number"]
            self.reaction_asm = value["reaction_asm"]
            self.reaction_state = value["reaction_state"]
        except json.decoder.JSONDecodeError:
            pass
    frame_number : bpy.props.IntProperty()
    reaction_asm : bpy.props.StringProperty()
    reaction_state : bpy.props.StringProperty()

class PlayEffectEventInfo(PropertyGroup):
    @property
    def info(self):
        return json.dumps({"frame_number" : self.frame_number, "vfx_name" : self.vfx_name, "actor" : self.actor, "bone" : self.bone,
                           "unused_zero" : self.unused_zero, "target_actor" : self.target_actor,
                           "target_bone" : self.target_bone, "unique_vfx_name" : self.unique_vfx_name})

    @info.setter
    def info(self, value):
        try:
            value = json.loads(value)
            self.frame_number = value["frame_number"]
            self.vfx_name = value["vfx_name"]
            self.actor = value["actor"]
            self.bone = value["bone"]
            self.unused_zero = value["unused_zero"]
            self.target_actor = value["target_actor"]
            self.target_bone = value["target_bone"]
            self.unique_vfx_name = value["unique_vfx_name"]
        except json.decoder.JSONDecodeError:
            pass
    frame_number : bpy.props.IntProperty()
    vfx_name : bpy.props.StringProperty()
    actor : bpy.props.StringProperty()
    bone: bpy.props.StringProperty()
    unused_zero : bpy.props.IntProperty()
    target_actor : bpy.props.StringProperty()
    target_bone : bpy.props.StringProperty()
    unique_vfx_name : bpy.props.StringProperty()
class EventUI:
    event_ui_list_name = ""
    def draw_all_instances(self, context, obj, layout):
        scene = context.scene
        if hasattr(obj, self.event_ui_list_name):
            event_list = getattr(obj, self.event_ui_list_name)
            if len(event_list) > 0:
                for idx, item in enumerate(event_list):
                    column = layout.column()
                    self.draw_event(context, column, item, idx)
            else:
                self.draw_create_event(layout)
        else:
            self.draw_create_event(layout)

    def draw_event(self, context, layout, item, idx):
        pass

    def get_blender_class_to_register(self):
        raise NotImplementedError("Subclasses must implement this method to return the Blender class to register.")

    def draw_options(self, layout, idx):
        layout.operator('s4animtools.move_new_element', text='↑').args = f"{self.event_ui_list_name},{idx},up"
        layout.operator('s4animtools.move_new_element', text='↓').args = f"{self.event_ui_list_name},{idx},down"
        layout.operator('s4animtools.move_new_element', text='✖').args = f"{self.event_ui_list_name},{idx},delete"
        layout.operator('s4animtools.move_new_element', text='+').args = f"{self.event_ui_list_name},{idx},create"

    def draw_create_event(self, layout):
        layout.operator('s4animtools.move_new_element', text='+').args = f"{self.event_ui_list_name},{0},create"

    def get_corresponding_list_count(self, obj):
        if hasattr(obj, self.event_ui_list_name):
            return len(getattr(obj, self.event_ui_list_name))
        return 0


    def register_blender_class(self):
        cls_to_register = self.get_blender_class_to_register()
        bpy.utils.register_class(cls_to_register)
        setattr(bpy.types.Object, self.event_ui_list_name, CollectionProperty(type=cls_to_register))


    def unregister_blender_class(self):
        if hasattr(bpy.types.Object, self.event_ui_list_name):
            delattr(bpy.types.Object, self.event_ui_list_name)
        bpy.utils.unregister_class(self.get_blender_class_to_register())


class SoundEventUI(EventUI):
    event_ui_list_name = "sound_events_list_UI"

    def get_blender_class_to_register(self):
        return SoundEventInfo

    def draw_event(self, context, layout, item, idx):
        layout.row().prop(item, "frame_number", text="Frame")
        layout.row().prop(item, "sound_name", text="Sound")
        right_row = layout.row()
        right_row.scale_x = 0.3
        self.draw_options(right_row, idx)
        layout.row().label(text="")



class ParentEventUI(EventUI):
    event_ui_list_name = "parent_events_list_UI"

    def get_blender_class_to_register(self):
        return ParentEventInfo

    def draw_event(self, context, layout, item, idx):
        layout.row().prop(item, "frame_number", text="Frame")
        if context.scene.use_picker_ui:
            layout.row().prop_search(item, "child_actor", context.scene, "objects", text="Child Actor")
            layout.row().prop_search(item, "parent_actor", context.scene, "objects", text="Parent Actor")
            if item.parent_actor != "":
                layout.row().prop_search(item, "parent_bone", context.scene.objects[item.parent_actor].pose,
                                              "bones",
                                              text="Parent Bone")
        else:
            layout.row().prop(item, "child_actor", text="Child Actor")
            layout.row().prop(item, "parent_actor", text="Parent Actor")
            if item.parent_actor != "":
                layout.row().prop(item, "parent_bone", text="Parent Bone")

        right_row = layout.row()
        right_row.scale_x = 0.3
        self.draw_options(right_row, idx)
        layout.row().label(text="")



class ReactionEventUI(EventUI):
    event_ui_list_name = "reaction_events_list_UI"

    def get_blender_class_to_register(self):
        return ReactionEventInfo

    def draw_event(self, context, layout, item, idx):
        layout.row().prop(item, "frame_number", text="Frame")
        layout.row().prop(item, "reaction_asm", text="Reaction ASM")
        layout.row().prop(item, "reaction_state", text="Reaction State")
        right_row = layout.row()
        right_row.scale_x = 0.3
        self.draw_options(right_row, idx)
        layout.row().label(text="")

class SnapEventUI(EventUI):
    event_ui_list_name = "snap_events_list_UI"

    def get_blender_class_to_register(self):
        return SnapEventInfo

    def draw_event(self, context, layout, item, idx):
        layout.row().prop(item, "frame_number", text="Frame")
        if context.scene.use_picker_ui:
            layout.row().prop_search(item, "target_actor", context.scene, "objects", text="Target Actor")
            if item.target_actor != "" and item.target_actor in context.scene.objects:
                layout.row().prop_search(item, "target_bone", context.scene.objects[item.target_actor].pose,
                                                  "bones",
                                                  text="Target Bone")
            if item.target_actor not in context.scene.objects:
                layout.row().label(text="Target Actor not found in scene, please select a valid target actor.")
        else:
            layout.row().prop(item, "target_actor", text="Target Actor")
            layout.row().prop(item, "target_bone", text="Target Bone")

        right_row = layout.row()
        right_row.scale_x = 0.3
        self.draw_options(right_row, idx)
        layout.row().label(text="")


class ScriptEventUI(EventUI):
    event_ui_list_name = "script_events_list_UI"

    def get_blender_class_to_register(self):
        return ScriptEventInfo

    def draw_event(self, context, layout, item, idx):
        layout.row().prop(item, "frame_number", text="Frame")
        layout.row().prop(item, "event_id", text="Xevt ID")
        right_row = layout.row()
        right_row.scale_x = 0.3
        self.draw_options(right_row, idx)
        layout.row().label(text="")

class VisibilityEventUI(EventUI):
    event_ui_list_name = "visibility_events_list_UI"

    def get_blender_class_to_register(self):
        return VisibilityEventInfo

    def draw_event(self, context, layout, item, idx):
        if context.scene.use_picker_ui:
            layout.row().prop_search(item, "actor", context.scene, "objects", text="Actor")
        else:
            layout.row().prop(item, "actor", text="Actor")
        layout.row().prop(item, "visibility", text="Visibility")
        right_row = layout.row()
        right_row.scale_x = 0.3
        self.draw_options(right_row, idx)
        layout.row().label(text="")


class PlayEffectEventUI(EventUI):
    event_ui_list_name = "play_effect_events_list_UI"

    def get_blender_class_to_register(self):
        return PlayEffectEventInfo

    def draw_event(self, context, layout, item, idx):
        layout.row().prop(item, "frame_number", text="Frame")
        layout.row().prop(item, "vfx_name", text="VFX Name")
        if context.scene.use_picker_ui:
            layout.row().prop_search(item, "actor", context.scene, "objects", text="Actor")
            if item.actor != "" and item.actor in context.scene.objects:
                layout.row().prop_search(item, "bone", context.scene.objects[item.actor].pose,
                                                  "bones",
                                                  text="Bone")
            if item.actor not in context.scene.objects:
                layout.row().label(text="Actor not found in scene, please select a valid actor.")
            layout.row().prop_search(item, "target_actor", context.scene, "objects", text="Target Actor")
            if item.target_actor != "" and item.target_actor in context.scene.objects:
                layout.row().prop_search(item, "target_bone", context.scene.objects[item.target_actor].pose,
                                                  "bones",
                                                  text="Target Bone")
            if item.target_actor not in context.scene.objects:
                if item.target_actor != "":
                    layout.row().label(text="Target Actor not found in scene, please select a valid target actor.")
        else:
            layout.row().prop(item, "actor", text="Actor")
            if item.actor not in context.scene.objects:
                layout.row().label(text="Actor not found in blender scene.")
            layout.row().prop(item, "bone", text="Bone")
            layout.row().prop(item, "target_actor", text="Target Actor")
            if item.target_actor not in context.scene.objects:
                if item.target_actor != "":
                    layout.row().label(text="Target Actor not found in blender scene.")
            layout.row().prop(item, "target_bone", text="Target Bone")

        layout.row().prop(item, "unique_vfx_name", text="Unique VFX Name")
        right_row = layout.row()
        right_row.scale_x = 0.3
        self.draw_options(right_row, idx)
        layout.row().label(text="")