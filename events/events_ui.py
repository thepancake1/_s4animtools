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