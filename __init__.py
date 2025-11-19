import bpy
import os
import time
import math

import s4animtools.bone_names
from s4animtools.bone_tester import is_third_left_finger_joint, is_third_right_finger_joint
from s4animtools.ik_manager import IKTarget, TimeRange
from s4animtools.events.events_ui import (AnimationEvent, SoundEventInfo, SnapEventInfo, ScriptEventInfo,
                                          ParentEventInfo,
                                          VisibilityEventInfo, ReactionEventInfo, PlayEffectEventInfo,
                                          ParentEventUI, SoundEventUI,
                                          ReactionEventUI, SnapEventUI, ScriptEventUI, VisibilityEventUI,
                                          PlayEffectEventUI)
from s4animtools.rig.ik_chains import S4ANIMTOOLS_OT_CreateIKChain, S4ANIMTOOLS_OT_CreateBones, \
    S4ANIMTOOLS_OT_FKIKSwitch, S4ANIMTOOLS_OT_IKFKSwitch, S4ANIMTOOLS_OT_LoadPresetBoneConfig
from s4animtools.serialization.fnv import get_64bithash, get_32bit_hash
from s4animtools.rcol.rcol_wrapper import OT_S4ANIMTOOLS_ImportFootprint, OT_S4ANIMTOOLS_VisualizeFootprint, \
    OT_S4ANIMTOOLS_ExportFootprint
from s4animtools.rig.create_rig import Trackmask
from s4animtools.rig_tools import ExportRig, SyncRigToMesh
from s4animtools.events.events import SnapEvent, SoundEvent, ScriptEvent, ReactionEvent, VisibilityEvent, ParentEvent, \
    PlayEffectEvent, FocusCompatibilityEvent, SuppressLipsyncEvent, StopEffectEvent, GeometryStateChangeEvent
from s4animtools.serialization.types.basic import f32, u32
from s4animtools.clip_processing.clip_header import ClipResource, bone_to_slot_offset_idx
from s4animtools.ik_baker import s4animtool_OT_bakeik, get_ik_targets, get_ik_targets_for_chain_bone, \
    get_ik_target_idx_for_slot_assignment_on_chain

from s4animtools.rig.create_rig import create_rig_with_context
import s4animtools.clip_processing.clip_header
import s4animtools.rig
import s4animtools.channels.f1_normalized_channel
import s4animtools.channels.translation_channel
import s4animtools.channels.loco_channel
import s4animtools.channels.palette_channel
import s4animtools.channels.quaternion_channel
import s4animtools.control_rig.basic_control_rig
import s4animtools.frames.frame
from s4animtools.control_rig.basic_control_rig import CopyLeftSideAnimationToRightSide, \
    CopySelectedLeftSideToRightSide, CopyLeftSideAnimationToRightSideSim, CopyBakedAnimationToControlRig, FlipLeftSideAnimationToRightSideSim
from s4animtools.ik_manager import BeginIKMarker, LIST_OT_NewIKTarget, LIST_OT_CreateIKTarget, LIST_OT_DeleteIKTarget, \
    LIST_OT_MoveIKTarget, \
    s4animtool_OT_removeIK, s4animtool_OT_mute_ik, s4animtool_OT_unmute_ik, LIST_OT_NewIKRange, LIST_OT_DeleteIKRange, \
    LIST_OT_DeleteSpecificIKTarget, MAX_SUBROOTS, s4animtools_OT_guessTarget, IKTarget, S4ANIMTOOLS_OT_DeleteAllIKTargets
import s4animtools.animation_exporter.animation
from s4animtools.animation_exporter.animation import AnimationExporter, AdditiveAnimationExporter
import s4animtools.rig.create_rig
from s4animtools.serialization.types.transforms import Vector3, Quaternion
from s4animtools.clip_operators import OT_S4ANIMTOOLS_CreateClipData, get_formatted_clip_name, \
    OT_S4ANIMTOOLS_InitializeThumbnails
import s4animtools.clip_processing.clip_body
import s4animtools.clip_processing.f1_palette
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector, Matrix
from bpy.props import IntProperty, CollectionProperty, FloatProperty, StringProperty, BoolProperty
from bpy.types import PropertyGroup
from collections import defaultdict

from s4animtools.slot_assignments import SlotAssignment
from s4animtools.walkstyles.blender import LocomotionBuilderVariantData, draw_locomotion_builder_data, locomotion_register, \
    locomotion_unregister
from s4animtools.control_rig.sticky_bones import OT_S4ANIMTOOLS_PreviewSlotAssignment, \
    OT_S4ANIMTOOLS_PreviewAllSlotAssignments

CURRENT_S4ANIMTOOLS_VERSION = 2
JAW_ANIMATE_DURATION = 100000


CHAIN_STR_IDX = 2
bl_info = {"name": "s4animtools", "category": "Object", "blender": (2, 80, 0)}

parent_events_holder = ParentEventUI()
sound_events_holder = SoundEventUI()
reaction_events_holder = ReactionEventUI()
snap_events_holder = SnapEventUI()
script_events_holder = ScriptEventUI()
visibility_events_holder = VisibilityEventUI()
play_effect_events_holder = PlayEffectEventUI()
all_event_holders = [parent_events_holder, sound_events_holder,
                     reaction_events_holder, snap_events_holder,
                     script_events_holder, visibility_events_holder,
                      play_effect_events_holder]

def determine_ik_slot_targets(rig):
    all_constraints = defaultdict(list)
    current_bone_idx = defaultdict(int)

    for ik_target in get_ik_targets(rig):
        target_bone = ik_target.target_bone
        is_subroot_bone = False
        subroot_suffix = 0
        for subroot_suffix in range(MAX_SUBROOTS):
            is_subroot_bone = ik_target.target_bone.endswith(f"_{subroot_suffix}")
            if is_subroot_bone:
                break
        if is_subroot_bone:
            target_bone = ik_target.target_bone.replace(f"_{subroot_suffix}", "_")
        if ik_target.chain_idx == -1:
            chain_idx = bone_to_slot_offset_idx[ik_target.chain_bone]
        else:
            chain_idx = ik_target.chain_idx
        print(f"IK target {ik_target.target_obj} is on chain {ik_target.chain_bone}")
        all_constraints[ik_target.chain_bone].append(SlotAssignmentBlender(source_rig=rig,
                                                                       source_bone=ik_target.chain_bone,
                                                                       target_rig=bpy.data.objects[ik_target.target_obj],
                                                                       target_bone=target_bone,
                                                                       chain_idx=chain_idx,
                                                                       slot_assignment_idx=current_bone_idx[ik_target.chain_bone]))
        current_bone_idx[ik_target.chain_bone] += 1
    #print(",".join(all_constraints))
    return all_constraints


def create_ik_weight_channels(bone_name, influences, sequence_count):
    f1normalized_channel = s4animtools.channels.f1_normalized_channel.F1Normalized(bone_name, 5, 14 + sequence_count)
    min_value, max_value = min(influences.values()), max(influences.values())
    offset = (min_value + max_value) / 2
    scale = -((min_value - max_value) / 2)
    if round(scale, 4) == 0:
        scale = 1
    f1normalized_channel.set_channel_data(offset=offset, scale=scale, individual_frames=influences)
    return f1normalized_channel


def gather_ik_weights(obj, influences, bone_name, ik_weight_idx, start_frame, current_frame, last_frame_influence):
    """Record the IK weight of each IK constraint from the ik weight in Blender."""
    # print(last_frame_influence - constraint.influence)
    influence = getattr(obj.pose.bones[bone_name], f'ik_weight_{ik_weight_idx}')
    if current_frame - start_frame == 0 or abs(last_frame_influence - influence) > 0.001:
        influences[(bone_name, ik_weight_idx)][current_frame - start_frame] = influence
        return influence
    return last_frame_influence


def set_loco_world_ik(bone_name, clip_start, clip_end):
    """Record the IK weight of each IK constraint from the actual constraint in Blender."""
    f1normalized_channel = s4animtools.channels.f1_normalized_channel.F1Normalized(bone_name, 5, 14)
    influences = {}
    min_value, max_value = 1, 1
    influences[0] = 1
    influences[clip_end - clip_start] = 1

    # print(min_value, max_value)

    offset = (min_value + max_value) / 2
    scale = -((min_value - max_value) / 2)
    if scale == 0:
        scale = 1
    f1normalized_channel.set_channel_data(offset=offset, scale=scale, individual_frames=influences)
    return f1normalized_channel


class Snapper(bpy.types.Operator):
    bl_idname = "s4animtools.snap"
    bl_label = "Snap IK Target"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Does this thing actally still work?"""
        active_pose_bone = bpy.context.active_pose_bone
        x = bpy.data.objects["dude1"]

        y = bpy.data.objects["rig.001"]
        y_bones = y.pose.bones

        y_scores = {}
        y_translations = {}
        for bone in y_bones:
            if bone.name.endswith("slot"):
                target_matrix_final = y.matrix_world @ bone.matrix
                active_bone_matrix_final = x.matrix_world @ active_pose_bone.matrix

                distance_of_bone = (active_bone_matrix_final.translation - target_matrix_final.translation).length
                y_scores[bone.name] = distance_of_bone
                y_translations[bone.name] = target_matrix_final.translation
        top_y_bone = sorted(y_scores.items(), key=lambda x: x[1])[0][0]
        context.scene.IK_bone_target = top_y_bone

        bpy.data.objects["Cube"].location = y_translations[top_y_bone]
        print(top_y_bone, y_scores[top_y_bone])
        print(time.time())
        return {'FINISHED'}



class ClipInfo:
    def __init__(self, start_frame, end_frame, name, reference_namespace_hash, explicit_namespaces, initial_offset_q,
                 initial_offset_t, rig_name, loco):
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.name = name
        if reference_namespace_hash == "":
            reference_namespace_hash = 0
        else:
            reference_namespace_hash = int(reference_namespace_hash, 16)
        self.reference_namespace_hash = reference_namespace_hash
        self.explicit_namespaces = explicit_namespaces
        self.initial_offset_q = initial_offset_q
        self.initial_offset_t = initial_offset_t
        self.rig_name = rig_name
        self.loco = loco

    def __str__(self):
        return (f"\nName: {self.name}\n"
            f"Start Frame: {self.start_frame} End Frame: {self.end_frame}, \n"
                f"Reference Namespace Hash: {hex(self.reference_namespace_hash)}\n"
                f"Explicit Namespaces: {self.explicit_namespaces}\n"
                f"Initial Offset Q: {self.initial_offset_q}\n"
                f"Initial Offset T: {self.initial_offset_t}")
    def __repr__(self):
        return self.__str__()
class SlotAssignmentBlender:
    def __init__(self, source_rig, source_bone, target_rig, target_bone, slot_assignment_idx, chain_idx):
        self.source_rig = source_rig
        self.source_bone = source_bone
        self.target_rig = target_rig
        self.target_bone = target_bone
        self.slot_assignment_idx = slot_assignment_idx
        self.chain_idx = chain_idx

class NewClipExporter:

    def __init__(self):
        self.context = None
        self.additive = False
        self.clip_infos = []

    def setup_events(self, context, current_clip, start_frame, frame_count, additional_snap_frames, sampling_rate):
        """Shifts the timestamps of the clip events depending on the split.
        So you can time it relative to the start of the blend file in blender,
        and have it reflect relative to the clip file in the export.
        """
        start_time = start_frame * (1 / 30)
        frame_time = frame_count * (1 / 30)
        if sampling_rate == 2:
            frame_time /= 2
        variable_to_event = {context.object.parent_events_list: ParentEvent,
                             context.object.sound_events_list: SoundEvent,
                             context.object.snap_events_list: SnapEvent,
                             context.object.visibility_events_list: VisibilityEvent,
                             context.object.script_events_list: ScriptEvent,
                             context.object.reaction_events_list: ReactionEvent,
                             context.object.play_effect_events_list: PlayEffectEvent,
                             context.object.focus_compatibility_events_list: FocusCompatibilityEvent,
                             context.object.disable_lipsync_events_list: SuppressLipsyncEvent,
                             context.object.stop_effect_events_list: StopEffectEvent,
                             context.object.geometry_state_change_events_list: GeometryStateChangeEvent,}


        snap_frames = []

        # New UI Sound events widget
        # These ones have separate parameter fields
        for event in context.object.sound_events_list_UI:
            original_timestamp = event.frame_number
            original_timestamp, timeshifted_timestamp = self.create_timeshifted_timestamp(original_timestamp,
                                                                                          start_time,
                                                                                          sampling_rate=sampling_rate)
            if frame_time >= timeshifted_timestamp >= 0:
                current_clip.add_event(SoundEvent(timeshifted_timestamp, event.sound_name))

        for event in context.object.snap_events_list_UI:
            original_timestamp_frame = event.frame_number
            original_timestamp, timeshifted_timestamp = self.create_timeshifted_timestamp(original_timestamp_frame,
                                                                                          start_time,
                                                                                          sampling_rate=sampling_rate)
            snap_frames.append(math.floor(timeshifted_timestamp * 30))
            print("Snap frames: {}".format(snap_frames))
            target_rig_object = context.scene.objects[event.target_actor]
            if target_rig_object.rig_name.strip() == "":
                raise Exception(f"Targeting {target_rig_object}, but it has no rig name. This will not work so fix this and try again")


            # For snap events, the event must start on the first frame the sim is snapped on. NOT the frame where before they snap
            context.scene.frame_set(original_timestamp_frame)
            active_rig = context.object
            active_rig_root = context.object.pose.bones['b__ROOT__Adjust']
            target_rig = target_rig_object
            target_rig_root = target_rig.pose.bones[event.target_bone]

            translation, rotation = get_offset(active_rig, active_rig_root, target_rig, target_rig_root)

            if frame_time >= timeshifted_timestamp >= 0:
                current_clip.add_event(SnapEvent(timeshifted_timestamp,  target_rig_object.rig_name.strip(),
                                                 str(round(translation[0], 4)), str(round(translation[1], 4)), str(round(translation[2], 4)),
                                                 str(round(rotation[1], 4)), str(round(rotation[2], 4)), str(round(rotation[3], 4)), str(round(rotation[0], 4))))

        for event in context.object.script_events_list_UI:
            event : ScriptEventInfo
            original_timestamp = event.frame_number
            original_timestamp, timeshifted_timestamp = self.create_timeshifted_timestamp(original_timestamp,
                                                                                          start_time,
                                                                                          sampling_rate=sampling_rate)
            if frame_time >= timeshifted_timestamp >= 0:
                current_clip.add_event(ScriptEvent(timeshifted_timestamp, event.event_id))
        for event in context.object.parent_events_list_UI:
            event : ParentEventInfo
            original_timestamp = event.frame_number
            original_timestamp, timeshifted_timestamp = self.create_timeshifted_timestamp(original_timestamp,
                                                                                          start_time,
                                                                                          sampling_rate=sampling_rate)
            if frame_time >= timeshifted_timestamp >= 0:
                current_clip.add_event(ParentEvent(timeshifted_timestamp, event.child_actor, event.parent_actor,
                                                   event.parent_bone))

        for event in context.object.visibility_events_list_UI:
            event : VisibilityEventInfo
            original_timestamp = event.frame_number
            original_timestamp, timeshifted_timestamp = self.create_timeshifted_timestamp(original_timestamp,
                                                                                          start_time,
                                                                                          sampling_rate=sampling_rate)
            if frame_time >= timeshifted_timestamp >= 0:

                # If event.visibility is false, then set it to 0, otherwise set it to 1.
                current_clip.add_event(VisibilityEvent(timeshifted_timestamp, event.actor, 1 if event.visibility else 0 ))

        for event in context.object.reaction_events_list_UI:
            event : ReactionEventInfo
            original_timestamp = event.frame_number
            original_timestamp, timeshifted_timestamp = self.create_timeshifted_timestamp(original_timestamp,
                                                                                          start_time,
                                                                                          sampling_rate=sampling_rate)
            if frame_time >= timeshifted_timestamp >= 0:
                current_clip.add_event(ReactionEvent(timeshifted_timestamp, event.reaction_asm, event.reaction_state))

        for event in context.object.play_effect_events_list_UI:
            event: PlayEffectEventInfo
            original_timestamp = event.frame_number
            original_timestamp, timeshifted_timestamp = self.create_timeshifted_timestamp(original_timestamp,
                                                                                            start_time,
                                                                                            sampling_rate=sampling_rate)
            if frame_time >= timeshifted_timestamp >= 0:
                current_clip.add_event(PlayEffectEvent(timeshifted_timestamp, event.vfx_name, event.actor,
                                                       event.bone, event.unused_zero, event.target_actor,event.target_bone,
                                                       event.unique_vfx_name))
        for parameter_fields, event in variable_to_event.items():
            for event_instance in parameter_fields:
                parameters = event_instance.info.split(",")
                parameter_length = len(parameters)
                # If parameter length is not filled out, there are no parameters at all
                if parameter_length == 1:
                    continue
                # If there are less parameters than the event needs, raise an exception
                if parameter_length < event.arg_count:
                    raise Exception(
                        f"Your event {event.__name__} has incomplete parameters. Expected {event.arg_count} parameters. Got {parameter_length}")
                original_timestamp = parameters[0].strip()
                # If the first parameter, the timestamp, starts with //, this event has been disabled and ignore it.
                if original_timestamp.startswith("//"):
                    continue

                # Original timestamp is the time in seconds the event has been to occur on.
                # If there is only one clip in this sequence, it doesn't matter, these are the same.
                # if there are multiple clips, timeshifted timestamp is the time within the clip itself.

                # Say yopu have two clips, clip1, and clip2. Clip1 takes 10 frames, while Clip2 takes 25 frames.
                # If your clip event is at frame 10, or timestamp 0.333333. It will be considered as part of the next animation
                # at timeshifted timestamp 0.0 and frame 0.

                # I should probably clean up the distinction between frames and timestamps, but it works, and only one
                # frame rate is supported by the game, so it's not *THAT* confusing.

                original_timestamp, timeshifted_timestamp = self.create_timeshifted_timestamp(original_timestamp, start_time, sampling_rate=sampling_rate)
                if event == SnapEvent:
                    if frame_time >= timeshifted_timestamp >= 0:

                        snap_frames.append(math.floor(timeshifted_timestamp * 30))
                        current_clip.add_event(event(timeshifted_timestamp, *parameters[1:]))

                # if event type is Focus Compatibility or Suppress Lipsync, create timeshifted timestamps for both start and end.
                elif event == FocusCompatibilityEvent:
                    if frame_time >= timeshifted_timestamp >= 0:
                        _, timeshifted_end_timestamp = self.create_timeshifted_timestamp(parameters[1].strip(),
                                                                                         start_time, sampling_rate=sampling_rate)
                        current_clip.add_event(
                            event(timeshifted_timestamp, timeshifted_end_timestamp, *parameters[2:]))
                elif event == SuppressLipsyncEvent:
                    if frame_time >= timeshifted_timestamp >= 0:
                        _, timeshifted_end_timestamp = self.create_timeshifted_timestamp(parameters[1].strip(),
                                                                                         start_time, sampling_rate=sampling_rate)
                        current_clip.add_event(
                            event(timeshifted_timestamp, timeshifted_end_timestamp, *parameters[2:]))
                else:
                    if frame_time >= timeshifted_timestamp >= 0:
                        current_clip.add_event(event(timeshifted_timestamp, *parameters[1:]))

        # Force enable the jaw to animate for the entire animation.
        if context.object.allow_jaw_animation_for_entire_animation:
            current_clip.add_event(SuppressLipsyncEvent(0, JAW_ANIMATE_DURATION))
        # Additional snap frames, handy for weird blending between different frames.
        # Originally used for snap events, but this flag gets set automatically on snap events now.
        if additional_snap_frames != "":
            additional_snap_frames = additional_snap_frames.split(",")
            for frame in additional_snap_frames:
                original_frame = int(frame)
                timeshifted_frame = original_frame - start_frame
                if frame_count > timeshifted_frame >= 0:
                    snap_frames.append(timeshifted_frame)
        return snap_frames

    def create_timeshifted_timestamp(self, original_timestamp_str, start_time:float, sampling_rate:int) -> tuple[float, float]:
        # This returns the frame count in 30 fps
        # For the new events widgets that are ui based instead of being a sad csv
        if isinstance(original_timestamp_str, int):
            # / 30 for frame to second, then sampling rate for 60 to 30 downsample
            original_timestamp = original_timestamp_str / 30

        else:
            if original_timestamp_str.endswith("s"):
                original_timestamp = float(original_timestamp_str[:-1])
            elif original_timestamp_str.endswith("e"):
                original_timestamp = float(eval(original_timestamp_str[:-1]))
            # Float mode (f mode) very redundant since https://github.com/thepancake1/_s4animtools/commit/39cd6430cc5cf82dd9022c9011de8e2e342b7267
            elif original_timestamp_str.endswith("f"):
                original_timestamp = float(original_timestamp_str[:-1]) / 30
            else:
                original_timestamp = float(original_timestamp_str) / 30

        timeshifted_timestamp = original_timestamp - start_time


        if sampling_rate == 2:
            original_timestamp = original_timestamp / 2
            timeshifted_timestamp = timeshifted_timestamp / 2
        return original_timestamp, timeshifted_timestamp
    def get_clip_names(self) -> list[str]:
        clip_names = []
        if self.context.scene.clip_name == "":
            raise Exception("You need to specify a clip name")
        clip_input_names = self.context.scene.clip_name.split(",")
        if len(clip_input_names) > 0:
            for clip_input_name in clip_input_names:
                if self.context.scene.clip_name_prefix == "":
                    clip_names.append(clip_input_name)
                else:
                    clip_names.append(f"{self.context.scene.clip_name_prefix}_{clip_input_name}")
        return clip_names
    def get_clip_names_with_actor_suffix(self) -> list[str]:
        clip_names = self.get_clip_names()
       # This object supports rig suffixes, will stick them on to the end.

        if not self.context.object.disable_rig_suffix:
            for idx in range(clip_names):
                clip_names[idx] += "_" + self.context.opbject.rig_name

        return clip_names

    def get_clip_splits(self) -> list[int]:
        clip_indices = [0, ]
        clip_splits = self.context.scene.clip_splits.split(",")
        # If the clip splits string is of zero length, then the user hasn't entered anything and needs to enter it.
        if len(self.context.scene.clip_splits) == 0:
            raise Exception("You need to specify clip splits")

        elif len(clip_splits) > 0:
            for split in clip_splits:
                clip_indices.append(int(split))
        return clip_indices

    def get_clip_locos(self) -> list[bool]:
        clip_locos_bool = []
        clip_locos = self.context.scene.clip_locos.split(",")
        # If the clip locos string is of zero length, then the user hasn't entered anything and needs to enter it.
        if len(self.context.scene.clip_locos) == 0:
            for split in self.get_clip_splits():
                clip_locos_bool.append(False)
        elif len(self.get_clip_splits()) - 1 != len(clip_locos):
            raise Exception("Clip splits does not match clip locos")
        elif len(clip_locos) > 0:
            for split in clip_locos:
                clip_locos_bool.append(split=="+")
        return clip_locos_bool

    def get_explicit_namespaces(self) -> str:
        return self.context.object.explicit_namespaces

    def get_reference_namespace_hash(self) -> str:
        return self.context.object.reference_namespace_hash

    def get_clip_infos(self) -> list[ClipInfo]:
        rig_name = self.context.object.rig_name
        if rig_name == "":
            raise Exception("You need to specify a rig name")
        initial_offset_t = self.context.object.initial_offset_t
        initial_offset_q = self.context.object.initial_offset_q
        # Set the initial offsets to the default if the user doesn't enter anything.
        # Should this be a string?
        if initial_offset_t == "":
            initial_offset_t = "0,0,0"
        if initial_offset_q == "":
            initial_offset_q = "0,0,0,1"
        clip_infos = []
        clip_names = self.get_clip_names()
        clip_indices = self.get_clip_splits()
        clip_locos = self.get_clip_locos()

        if len(clip_names) != len(clip_indices) - 1:
            raise ValueError(
                "Clip names doesn't match clip indices. Please check your splits and names are the same length.")
        for clip_idx in range(len(clip_names)):
            clip_infos.append(
                ClipInfo(start_frame=clip_indices[clip_idx], end_frame=clip_indices[clip_idx + 1], name=clip_names[clip_idx],
                         explicit_namespaces=self.get_explicit_namespaces(),
                         reference_namespace_hash=self.get_reference_namespace_hash(),
                         initial_offset_q=Quaternion.from_str(initial_offset_q),
                         initial_offset_t=Vector3.from_str(initial_offset_t), rig_name=rig_name, loco=clip_locos[clip_idx]))
        return clip_infos

    def get_downsampled_frame_idx(self, frame, sampling_rate):
        if sampling_rate == 1:
            return frame
        return frame // sampling_rate
    def execute(self, context):
        t1 = time.time()
        self.context = context

        export_as_loose_files = self.context.scene.export_as_loose_files

        # Check if the user has toggled 60 fps downsampling to 30 fps
        if self.context.scene.downsample_60_to_30:
            if bpy.context.scene.render.fps != 60:
                raise ValueError("You need to set your render settings to 60 fps to downsample to 30.")

        # Set the source filename in the exported clip to be this blend's filename.
        source_filename = f"{bpy.data.filepath.split(os.sep)[-1]} (Exported with Blender {bpy.app.version[0]}.{bpy.app.version[1]}.{bpy.app.version[2]})"
        ik_targets_to_bone = determine_ik_slot_targets(self.context.active_object)

        clip_infos = self.get_clip_infos()

        world_rig = self.context.object.world_rig
        world_root = self.context.object.world_bone

        # World Rig is a string here.
        if len(world_rig) == 0:
            world_rig = self.context.object
        else:
            world_rig = bpy.data.objects[world_rig]

        # World Root is a string here.
        if len(world_root) == 0:
            world_root = world_rig.pose.bones["b__ROOT__"]
        else:
            world_root = world_rig.pose.bones[world_root]

        base_rig = self.context.object.base_rig
        slot_assignments = []
        slot_idx = 0
        for chain_bone in ik_targets_to_bone:
            for idx, slot_assignment in enumerate(ik_targets_to_bone[chain_bone]):
                target_rig = slot_assignment.target_rig
                print("target rig is {}".format(target_rig))
                target_bone = slot_assignment.target_bone
                chain_idx = slot_assignment.chain_idx
                if "subroot" in target_bone:
                    target_bone = "b__ROOT__"
                if "loco" in target_bone:
                    target_bone = "b__ROOT__"
                if target_bone.endswith("Adjust"):
                    target_bone = target_bone.replace("Adjust", "")
                if chain_idx == -1:
                    chain_idx = bone_to_slot_offset_idx[slot_assignment.source_bone]
                sA = SlotAssignment(chain_idx, idx, target_rig.rig_name, target_bone)
                slot_assignments.append(sA)
                slot_idx += 1
        explicit_namespaces = []
        for idx, clip_info in enumerate(clip_infos):
            if len(clip_info.explicit_namespaces) >= 2:
                for namespace in clip_info.explicit_namespaces.split(","):
                    explicit_namespaces.append(namespace.lstrip())
            current_clip = ClipResource(clip_info.name, clip_info.rig_name, slot_assignments,
                                        explicit_namespaces,
                                        clip_info.reference_namespace_hash, clip_info.initial_offset_q,
                                        clip_info.initial_offset_t, source_filename, clip_info.loco, context.object.disable_rig_suffix)
            rig = self.context.object

            # sampling rate. 1 for every frame, 2 for every other frame, etc.
            # Currently used for halving the animation data for 60 fps to 30 fps.
            sampling_rate = 1
            if self.context.scene.downsample_60_to_30:
                sampling_rate = 2

            snap_frames = self.setup_events(self.context, current_clip, clip_info.start_frame, clip_info.end_frame - clip_info.start_frame,
                                            self.context.object.additional_snap_frames, sampling_rate=sampling_rate)

            if self.additive:
                exporter = AdditiveAnimationExporter(rig, snap_frames, world_rig=world_rig, world_root=world_root, use_full_precision=self.context.object.use_full_precision, base_rig=bpy.data.objects[base_rig], allow_slots=self.context.object.allow_slots, overlay=self.context.object.is_overlay)
            else:
                exporter = AnimationExporter(rig, snap_frames, world_rig=world_rig, world_root=world_root, use_full_precision=self.context.object.use_full_precision, allow_slots=self.context.object.allow_slots, overlay=self.context.object.is_overlay)
            exporter.create_animation_data()
            exporter.paletteHolder.try_add_palette_to_palette_values(0)
            exporter.paletteHolder.try_add_palette_to_palette_values(1.0)

            last_frame_influences = defaultdict(int)
            ik_weight_animation_data = defaultdict(dict)

            slot_assignment_source_bones = ik_targets_to_bone.keys()



            # The +1 is for ensuring the last frame is included in the downsampled animation data.
            # Selectively add + 1 to the end frame if the sampling rate is 2, and don't add anything if the sampling rate is 1.
            # Previous versions would *always* add +1, which would cause walkstyles to absolutely break
            # Need to clean this up one of these days
            end_frame_offset = 0
            if sampling_rate == 2:
                end_frame_offset = 1
            for frame_idx in range(clip_info.start_frame, clip_info.end_frame+end_frame_offset, sampling_rate):
                bpy.context.scene.frame_set(frame_idx)
                bpy.context.view_layer.update()
                exporter.animate_recursively(self.get_downsampled_frame_idx(frame_idx, sampling_rate), start_frame=self.get_downsampled_frame_idx(clip_info.start_frame, sampling_rate), force=frame_idx == clip_info.start_frame
                                                              or frame_idx == clip_info.end_frame)
                # Please shorten this!
                # These lines are too wide!
                for source_bone_ik in slot_assignment_source_bones:
                    for ik_idx, slot_assignment_info in enumerate(ik_targets_to_bone[source_bone_ik]):

                        ik_weight = gather_ik_weights(rig, ik_weight_animation_data, slot_assignment_info.source_bone, ik_idx, self.get_downsampled_frame_idx(clip_info.start_frame, sampling_rate),
                                                      self.get_downsampled_frame_idx(frame_idx, sampling_rate), last_frame_influences[(slot_assignment_info.source_bone, ik_idx)])
                        last_frame_influences[(slot_assignment_info.source_bone, ik_idx)] = ik_weight

            for source_bone_ik in slot_assignment_source_bones:
                for ik_idx, slot_assignment_info in enumerate(ik_targets_to_bone[source_bone_ik]):
                    exporter.add_baked_animation_data_to_frame(slot_assignment_info.source_bone,
                                                               start_frame=self.get_downsampled_frame_idx(clip_info.start_frame, sampling_rate),
                                                               end_frame=self.get_downsampled_frame_idx(clip_info.end_frame, sampling_rate), ik_idx=ik_idx, sampling_rate=sampling_rate)
                    current_clip.clip_body.add_channel((create_ik_weight_channels(slot_assignment_info.source_bone, ik_weight_animation_data[(slot_assignment_info.source_bone, ik_idx)], ik_idx)))

            for channel in exporter.export_to_channels():
                current_clip.clip_body.add_channel(new_channel=channel)
            current_clip.clip_body.set_palette_values(exporter.paletteHolder.palette_values)
            current_clip.update_duration(self.get_downsampled_frame_idx(clip_info.end_frame, sampling_rate)- self.get_downsampled_frame_idx(clip_info.start_frame, sampling_rate))

            current_clip.export(export_path=self.context.scene.s4animtools_export_path, alternative_export_path=self.context.scene.s4animtools_export_path2, export_as_loose_filenames=export_as_loose_files)
        t2 = time.time()
        print(f"Took {t2 - t1} seconds for clip export")
        return {"FINISHED"}

class OT_S4ANIMTOOLS_NewExportClip(bpy.types.Operator):
    bl_idname = "s4animtools.new_export_clip"
    bl_label = "New Export Clip"
    bl_options = {"REGISTER", "UNDO"}

    additive: BoolProperty(default=False)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anim_exporter = NewClipExporter()
        self.anim_exporter.additive = self.additive
    def execute(self, context):
        self.anim_exporter.execute(context)
        return {"FINISHED"}
class S4ANIMTOOL_OT_ExportAllClips(bpy.types.Operator):
    bl_idname = "s4animtools.export_all_clips"
    bl_label = "Export All Clips"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        for obj in bpy.data.objects:
            if obj.is_actor and obj.is_enabled_for_animation:
                with bpy.context.temp_override(object=obj):
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.s4animtools.new_export_clip("INVOKE_DEFAULT")

        return {"FINISHED"}
class S4ANIMTOOLS_PT_MainPanel(bpy.types.Panel):
    bl_idname = "S4ANIMTOOLS_PT_MainPanel"
    bl_label = "S4AnimTools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    # bl_category = "Tools"
    bl_category = "S4AnimTools"

    def draw_property_if_not_empty(self, obj, property_name, layout):
        if getattr(obj, property_name, "") != "":
            layout.prop(obj, property_name)

    def draw_events(self, obj, events_list_name, x_scale, description, event_name, layout, parameters=None, editable=True, corresponding_widget_list_count=0):
        # Editable parameter was added so I can disable the old sound effects event list from being used
        events_list = getattr(obj, events_list_name)
        #print(f"{obj} - {len(events_list)} - {events_list_name}")
        layout.label(
            text=f"{event_name}: {len(events_list) + corresponding_widget_list_count} - {description}")
        for idx, item in enumerate(events_list):
            row = layout.row()
            if item.info != "":
                if parameters is not None:
                    parameter_list = list(zip(parameters, item.info.split(",")))
                    for key, value in parameter_list:
                        layout.row().label(text=f"{key}: {value}")

                    for key in parameters[len(item.info.split(",") ):]:
                        layout.row().label(text=f"{key}: ?")
                    if len(parameters) > len(item.info.split(",")):
                        layout.row().label(text="Not enough parameters.")
                    if len(parameters) < len(item.info.split(",")):
                        layout.row().label(text="Too many parameters.")
            row2 = row.row()
            row.scale_x = x_scale

            row2.prop(item, "info", text="")


            row.operator('s4animtools.move_new_element', text='↑').args = f"{events_list_name},{idx},up"
            row.operator('s4animtools.move_new_element', text='↓').args = f"{events_list_name},{idx},down"
            row.operator('s4animtools.move_new_element', text='✖').args = f"{events_list_name},{idx},delete"
            if editable:
                row.operator('s4animtools.move_new_element', text='+').args = f"{events_list_name},{idx},create"
        #layout.label(text="")

    def draw(self, context):
        obj = context.object

        layout = self.layout
        old_version = False

        if context.scene.s4animtools_version != CURRENT_S4ANIMTOOLS_VERSION:
            old_version = True

        # There used to be a bug here where this used to be called obj and was causing it to replace the original obj defined just before.
        for obj_maybe_needs_update in context.scene.objects:
            if len(obj_maybe_needs_update.sound_events_list) > 0:
                old_version = True
                break
            if len(obj_maybe_needs_update.script_events_list) > 0:
                old_version = True
                break
            if len(obj_maybe_needs_update.parent_events_list) > 0:
                old_version = True
                break
            if len(obj_maybe_needs_update.reaction_events_list) > 0:
                old_version = True
                break
            if len(obj_maybe_needs_update.visibility_events_list) > 0:
                old_version = True
                break
            if len(obj_maybe_needs_update.play_effect_events_list) > 0:
                old_version = True
                break
        if old_version:
            layout.operator("s4animtools.upgrade_data", text="New version detected. Update file format to latest version?")
        layout.operator("s4animtools.select_export_path", icon='MESH_CUBE', text="Select Animation Export Path")
        layout.prop(context.scene, "s4animtools_export_path", text="Export Path")
     #   layout.prop(context.scene, "s4animtools_export_path2", text="Export Path 2")

   #     layout.prop(context.scene, "export_as_loose_files", text="Export Main as Loose Files, \n"
     #                                                            "2 as regular files")
     #   layout.prop(context.scene, "pose_pack_mode_enabled", text="Pose Pack Mode On")

        if obj is not None:
            box = layout.box()

            box.prop(obj, "is_actor", text="Is Actor")
            box.prop(obj, "is_enabled_for_animation", text="Is Enabled for Animation")

            if obj.is_actor:
                box.prop(obj, "actor_type", text="Actor Type")
                box.prop(obj, "game_type", text="Game Type")

                box.prop(obj, "rig_name", text="Rig Name")  # String for current clip actor

            if obj.is_enabled_for_animation:
                box = layout.box()

                row = box.row()
                #row.operator("s4animtools.create_clip_data", text=OT_S4ANIMTOOLS_CreateClipData.bl_label)
                #row.operator("s4animtools.initialize_thumbnails", text=OT_S4ANIMTOOLS_InitializeThumbnails.bl_label)
                #
                for idx, item in enumerate(context.scene.clips):
                    item : ClipData
                    row = box.row()
                    row.label(text="Clip #{}".format(idx))
                    box2 = box.box()
                    if not context.scene.pose_pack_mode_enabled:
                        formatted_clip_name = get_formatted_clip_name(item.clip_name, obj.rig_name)
                        box2.prop(item, "clip_name", text="Clip Name")
                        box2.label(text="Final clip name: {}".format(formatted_clip_name))
                    else:
                        formatted_clip_name = get_formatted_clip_name(item.clip_name, obj.rig_name)
                        if formatted_clip_name in bpy.data.textures:
                            tex = bpy.data.textures[formatted_clip_name]
                            col = box2.box().column()
                            col.template_preview(tex)
                        box2.prop(item, "clip_display_name", text="Clip Display Name")
                        box2.prop(item, "clip_description", text="Clip Description")
                    row = box2.row()
                    row.prop(item, "start_frame", text="Start Frame")
                    row.prop(item, "end_frame", text="End Frame")
                    box2.operator("s4animtools.create_clip_data", text=OT_S4ANIMTOOLS_CreateClipData.bl_label)

                box.prop(context.scene, "clip_splits", text="Clip Split Point(s)")
                box.prop(context.scene, "clip_name_prefix", text = "Clip Name Prefix")  # clip_name_prefix
                box.prop(context.scene, "clip_name", text = "Clip Name(s)")
                box.prop(obj, "allow_jaw_animation_for_entire_animation",
                                 text="Allow Jaw Animation For Entire Animation (Use this for poses or posepacks)")

                box.label(text="The center rig is where the root of your exported animation will be located.")
                box.label(text="Useful for poses with multiple sims.")
                box.prop_search(context.object, "world_rig", context.scene, "objects", text="Center Rig")
                if len(context.object.world_rig) > 0:
                    if context.object.world_rig in bpy.data.objects:
                        target_bone_obj = bpy.data.objects[obj.world_rig]
                        box.prop_search(context.object, "world_bone", target_bone_obj.pose, "bones", text="Center Bone")


                box.prop(obj, "explicit_namespaces", text="Explicit Namespaces")
                row = box.row()
                row.operator("s4animtools.new_export_clip", text="Export Clip")

                row.operator("s4animtools.export_all_clips", text="Export All Clips")
                box.prop(context.object, "animation_notes", text="Animation Notes", icon='TEXT')


            layout.prop(obj, "show_footprint_options", text="Show Footprint Options")
            if obj.show_footprint_options:
                row = layout.row()

                row.label(text="Footprint Name/Hash: ")
                row = layout.box().row()

                row.prop(context.object, "footprint_name", text="Text")


                layout.prop(obj, "is_footprint", text="Is Footprint Object")
                box = layout.box()

                row = box.row()
                row.operator("s4animtools.import_footprint", text="Import Footprint")
                row.operator("s4animtools.export_footprint", text="Export Footprint")

                row = layout.row()
                row.label(text="View footprints for:")
                box = layout.box()
                row = box.row()

                row.operator("s4animtools.visualize_footprint", text="Pathing").command="for_pathing"
                row.operator("s4animtools.visualize_footprint", text="Placement").command="for_placement"
                row = box.row()

                row.operator("s4animtools.visualize_footprint", text="Terrain").command="terrain"
                row.operator("s4animtools.visualize_footprint", text="Floor").command="floor"

                # workaround for 1 item in 2 columns
                row = box.row()
                col = row.column()
                col.operator("s4animtools.visualize_footprint", text="Pool").command="pool"
                col = row.column()
                col.label(text="")
                if obj.is_footprint:

                  #  layout.prop(obj, "footprint_resource_variant", text="Variant")

                   # layout.prop(obj, "is_routing_footprint", text="Is World Pathing Footprint")

                    row = layout.row()
                    layout.label(text="Footprint is in: ")
                    box = layout.box()
                    row = box.row()

                    row.prop(obj, "slope", text="Slope")
                    row.prop(obj, "outside", text="Outside")
                    row.prop(obj, "inside", text="Inside")
                    row = layout.row()

                    row.label(text="Footprint is of Type: ")

                    box = layout.box()
                    row = box.row()
                    row.prop(obj, "for_placement", text="For Placement")
                    row.prop(obj, "for_pathing", text="For Pathing")
                    row.prop(obj, "is_enabled", text="Is Enabled")
                    row = box.row()

                    row.prop(obj, "discouraged", text="Discouraged")
                    row.prop(obj, "landing_strip", text="Landing Strip")
                    row.prop(obj, "no_raycast", text="No Raycast")
                    row = box.row()

                    row.prop(obj, "placement_slotted", text="Placement Slotted")
                    row.prop(obj, "encouraged", text="Encouraged")
                    row.prop(obj, "terrain_cutout", text="Terrain Cutout")
                    row = layout.row()

                    row.label(text="Footprint is of Surface Type: ")

                    box = layout.box()
                    row = box.row()
                    row.prop(obj, "terrain", text="Terrain")
                    row.prop(obj, "floor", text="Floor")
                    row.prop(obj, "pool", text="Pool")
                    row = box.row()

                    row.prop(obj, "pond", text="Pond")
                    row.prop(obj, "fence_post", text="Fence Post")
                    row.prop(obj, "any_surface", text="Any Surface")
                    row = box.row()
                    # 2 items in three column needs this hacky workaround
                    col = row.column()
                    col.prop(obj, "air", text="Air")
                    col = row.column()

                    col.prop(obj, "roof", text="Roof")
                    col = row.column()
                    col.label(text="")

                    row = layout.row()

                    row.label(text="Footprint Is Of Object Type: ")

                    box = layout.box()
                    row = box.row()
                    row.prop(obj, "is_none", text="None")
                    row.prop(obj, "is_walls", text="Walls")
                    row.prop(obj, "is_objects", text="Objects")

                    row = box.row()
                    row.prop(obj, "is_sims", text="Sims")
                    row.prop(obj, "is_roofs", text="Roof")
                    row.prop(obj, "is_fences", text="Fence")
                    row = box.row()

                    row.prop(obj, "is_modular_stairs", text="Modular Stairs")
                    row.prop(obj, "is_objects_of_same_type", text="Objects of Same Type")
                    row.prop(obj, "is_columns", text="Columns")

                    row = box.row()
                    row.prop(obj, "is_reserved_space", text="Reserved Space")

                    row.prop(obj, "is_foundations", text="Foundations")
                    row.prop(obj, "is_fenestration_node", text="Fenestration Node")
                    row = box.row()

                    row.prop(obj, "is_trim", text="Trim")
                    row = layout.row()

                    row.label(text="Footprint Ignores Footprints of Object Type: ")

                    box = layout.box()
                    row = box.row()

                    row.prop(obj, "ignores_none", text="None")
                    row.prop(obj, "ignores_walls", text="Walls")
                    row.prop(obj, "ignores_objects", text="Objects")

                    row = box.row()
                    row.prop(obj, "ignores_sims", text="Sims")

                    row.prop(obj, "ignores_roofs", text="Roof")
                    row.prop(obj, "ignores_fences", text="Fence")
                    row = box.row()
                    row.prop(obj, "ignores_modular_stairs", text="Modular Stairs")
                    row.prop(obj, "ignores_objects_of_same_type", text="Objects of Same Type")
                    row.prop(obj, "ignores_columns", text="Columns")

                    row = box.row()
                    row.prop(obj, "ignores_reserved_space", text="Reserved Space")

                    row.prop(obj, "ignores_foundations", text="Foundations")

                    row.prop(obj, "ignores_fenestration_node", text="Fenestration Node")
                    row = box.row()

                    row.prop(obj, "ignores_trim", text="Trim")







            layout.prop(obj, "show_mirror_and_masking_options", text="Show Rig Options")

            if obj.show_mirror_and_masking_options:

                # Trackmasks are not working yet
                #layout.operator("s4animtools.apply_trackmask", icon='MESH_CUBE', text="Apply Trackmask")
                # self.box.operator("s4animtools.copy_left_side", icon='MESH_CUBE', text="Copy Left Side (Bed)")
                box = layout.box()
                row = box.row()
                row.operator("s4animtools.flip_left_side_sim", text="Flip Sim")
                row.operator("s4animtools.copy_left_side_sim", text="Copy Left Side to Right Side Sim")
                #layout.operator("s4animtools.copy_baked_animation", icon='MESH_CUBE', text="Copy Baked Animation")
                # self.layout.operator("s4animtools.copy_left_side_sim_selected", icon='MESH_CUBE', text="Copy Left Side (Sim) Selected")

                row = box.row()

                row.operator("s4animtools.maintain_keyframe",
                                     text="Maintain Keyframe").direction = "FORWARDS"
                row.operator("s4animtools.maintain_keyframe",
                                     text="Maintain Keyframe Backward").direction = "BACK"

                row = box.row()
                row.operator("s4animtools.import_rig", text="Import Rig")

                row.operator("s4animtools.export_rig", text="Export Rig")
            layout.prop(obj, "show_control_rig_options", text="Show Control Rig Options (EXPERIMENTAL)")
            if obj.show_control_rig_options:
                if context.object.type == "ARMATURE":
                    box = layout.box()

                    row = box.operator("s4animtools.load_preset_bone_config", text="Load Preset Bone Config")
                    row = box.row()

                    row.prop_search(context.object, "original_bone_01", context.object.pose, "bones",
                                    text="IK Chain Start")
                    row = box.row()

                    row.prop_search(context.object, "original_bone_02", context.object.pose, "bones",
                                    text="IK Chain Middle")
                    row = box.row()

                    row.prop_search(context.object, "original_bone_03", context.object.pose, "bones",
                                    text="IK Chain End")

                    row = box.row()
                    row.prop_search(context.object, "original_bone_04", context.object.pose, "bones",
                                    text="Pole Target")
                    row = box.row()

                    row.prop(context.object, "ik_bone_01_fk_name", text="St FK Name")
                    row.prop(context.object, "ik_bone_01_ik_name", text="St IK Name")
                    row = box.row()
                    row.prop(context.object, "ik_bone_02_fk_name", text="Mid FK Name")
                    row.prop(context.object, "ik_bone_02_ik_name", text="Mid IK Name")
                    row = box.row()
                    row.prop(context.object, "ik_bone_03_fk_name", text="End FK Name")
                    row.prop(context.object, "ik_bone_03_ik_name", text="End IK Name")
                    row = box.row()
                    row.prop(context.object, "ik_bone_04_ik_name", text="Holder Name")
                    row = box.row()
                    row.prop(context.object, "ik_bone_05_ik_name", text="Target Name")
                    row = box.row()
                    row.prop(context.object, "ik_bone_06_ik_name", text="Pole Name")
                    row = box.row()
                    row.prop(context.object, "ik_bone_07_ik_name", text="Pole Indicator ")
                    row = box.row()

                    row.operator("s4animtools.create_ik_chain", text="Create Arms IK Chain").to_build = "Arms"

                    row = box.row()
                    row.prop_search(context.object, "original_bone_11", context.object.pose, "bones",
                                    text="IK Chain Start")
                    row = box.row()

                    row.prop_search(context.object, "original_bone_12", context.object.pose, "bones",
                                    text="IK Chain Middle")
                    row = box.row()

                    row.prop_search(context.object, "original_bone_13", context.object.pose, "bones",
                                    text="IK Chain End")
                    row = box.row()
                    row.prop_search(context.object, "original_bone_14", context.object.pose, "bones",
                                    text="Pole Target")

                    row = box.row()
                    row.prop(context.object, "ik_bone_11_fk_name", text="St FK Name")
                    row.prop(context.object, "ik_bone_11_ik_name", text="St IK Name")
                    row = box.row()
                    row.prop(context.object, "ik_bone_12_fk_name", text="Mid FK Name")
                    row.prop(context.object, "ik_bone_12_ik_name", text="Mid IK Name")
                    row = box.row()
                    row.prop(context.object, "ik_bone_13_fk_name", text="End FK Name")
                    row.prop(context.object, "ik_bone_13_ik_name", text="End IK Name")
                    row = box.row()
                    row.prop(context.object, "ik_bone_14_ik_name", text="Holder Name")
                    row = box.row()
                    row.prop(context.object, "ik_bone_15_ik_name", text="Target Name")
                    row = box.row()
                    row.prop(context.object, "ik_bone_16_ik_name", text="Pole Name")
                    row = box.row()
                    row.prop(context.object, "ik_bone_17_ik_name", text="Pole Indicator Name")
                    row = box.row()
                    row.operator("s4animtools.create_ik_chain", text="Create Legs IK Chain").to_build = "Legs"
                    row = box.row()

                    row.prop(context.object, "left_arm_ik_enabled", text="Left Arm IK Enabled")
                    if context.object.left_arm_ik_enabled < 0.99:
                        row.operator("s4animtools.fk_to_ik_switch", text="Left Arm FK to IK").to_build = "LeftArm"
                    else:
                        row.operator("s4animtools.ik_to_fk_switch", text="Left Arm IK to FK").to_build = "LeftArm"
                    row = box.row()

                    row.prop(context.object, "right_arm_ik_enabled", text="Right Arm IK Enabled")

                    if context.object.right_arm_ik_enabled < 0.99:
                        row.operator("s4animtools.fk_to_ik_switch", text="Right Arm FK to IK").to_build = "RightArm"
                    else:
                        row.operator("s4animtools.ik_to_fk_switch", text="Right Arm IK to FK").to_build = "RightArm"
                    row = box.row()

                    row.prop(context.object, "left_leg_ik_enabled", text="Left Leg IK Enabled")
                    if context.object.left_leg_ik_enabled < 0.99:
                        row.operator("s4animtools.fk_to_ik_switch", text="Left Leg FK to IK").to_build = "LeftLeg"
                    else:
                        row.operator("s4animtools.ik_to_fk_switch", text="Left Leg IK to FK").to_build = "LeftLeg"
                    row = box.row()

                    row.prop(context.object, "right_leg_ik_enabled", text="Right Leg IK Enabled")
                    if context.object.right_leg_ik_enabled < 0.99:
                        row.operator("s4animtools.fk_to_ik_switch", text="Right Leg FK to IK").to_build = "RightLeg"
                    else:
                        row.operator("s4animtools.ik_to_fk_switch", text="Right Leg IK to FK").to_build = "RightLeg"
                    row = box.row()

                    row.prop(context.object, "baked_eye_animation_enabled", text="Baked Eye Animation Enabled")
                    row = box.row()

                    row.operator("s4animtools.create_bones", text="Create Bones")


            layout.prop(obj, "show_ik_options", text="Show Slot Assignments")
            if obj.show_ik_options:
                box = layout.box()
                row = box.row()

                row.operator("s4animtools.toggle_slots", text="Toggle Slots")
                row.operator("s4animtools.preview_all_slot_assignments", text="Preview All Slot Assignments")

                row = box.row()
                row.operator('iktarget.create_roots', text='Create World IK Channels')
                row.operator('s4animtools.delete_all_ik_channels', text='Delete All IK Channels')

                box = layout.row()

                if obj.ik_idx >= 0 and obj.ik_targets:
                    # These are called rows but are obviously columns?
                    row = box.column()

                    self.draw_all_ik_targets_of_type(context, obj, row, "b__L_Hand__")
                    row = box.column()

                    self.draw_all_ik_targets_of_type(context, obj, row, "b__R_Hand__")
                    box = layout.row()

                    row = box.column()

                    self.draw_all_ik_targets_of_type(context, obj, row, "b__L_Foot__")
                    row = box.column()

                    self.draw_all_ik_targets_of_type(context, obj, row, "b__R_Foot__")
                    box = layout.row()

                    row = box.column()
                    self.draw_all_ik_targets_of_type(context, obj, row, "b__ROOT_bind__")
                    row = box.column()

                    self.draw_all_ik_targets_of_type(context, obj, row, "")

                row = layout.row()
                # row.scale_x = 0.2
                #  row.operator('iktarget.move', text='Down').direction = 'DOWN'
                #  row.operator('iktarget.move', text='Up').direction = 'UP'
                row.operator('iktarget.new', text='New InGame IK Target').command = ""
                row = layout.row()

                row.operator("s4animtools.bakeik", text="Bake InGame IK Animation Data")
                #layout.operator("s4animtools.muteik", text="Mute IK")
                #layout.operator("s4animtools.unmuteik", text="Unmute IK")

                #layout.operator("s4animtools.removeik", text="Remove IK")

                #layout.operator("s4animtools.preview_ik", text="Preview IK")
                #layout.operator("s4animtools.update_ik_empties", text="Update IK Empties")
                row.scale_x = 1

            layout.prop(obj, "show_initial_offset_options", text="Show Initial Offset Options")
            if obj.show_initial_offset_options:
                box = layout.box()
                row = box.row()

                row.prop_search(context.object, "relative_rig", context.scene, "objects", text="Initial Offsets Rig")
                if len(context.object.relative_rig) > 0:
                    if context.object.relative_rig in bpy.data.objects:
                        relative_rig_obj = bpy.data.objects[context.object.relative_rig]
                        warn_user = True
                        if hasattr(relative_rig_obj, "pose"):
                            if hasattr(relative_rig_obj.pose, "bones"):
                                box.prop_search(context.object, "relative_bone", relative_rig_obj.pose, "bones",
                                                   text="Initial Offsets Bone")
                                warn_user = False

                        if warn_user:
                            box.label(text=f"The object you selected: ({context.object.relative_rig}) is not a rig.")
                    else:
                        box.label(text=f"The object you selected: ({context.object.relative_rig}) does not exist.")

                row = box.row()
                row.prop(obj, "initial_offset_q", text="Initial Offset Q")
                row = box.row()


                row.prop(obj, "initial_offset_t", text="Initial Offset T")
                row = box.row()

                row.prop(obj, "reference_namespace_hash", text="Reference Namespace Hash")

            layout.prop(obj, "show_events", text="Show Events")
            if obj.show_events:
                layout.prop(context.scene, "use_picker_ui", text="Use Picker UI")

                layout.operator("s4animtools.initialize_events", text="Initialize Events")


                self.draw_events(obj, "parent_events_list", 0.1,
                                 "Parameters (Frame/Object To Be Parented/Object To Be Parented To/Bone)",
                                 "Parent Events", layout,
                                 parameters=["Frame", "Object to Be Parented", "Object to be Parented To", "Bone"],
                                 corresponding_widget_list_count=parent_events_holder.get_corresponding_list_count(obj))


                parent_events_holder.draw_all_instances(context, obj, layout)

                self.draw_events(obj, "sound_events_list", 0.1, "Parameters (Frame Number/Sound Effect Name)",
                                 "Sound Events", layout, parameters=["Frame", "Sound Effect Name"], editable=False,
                                 corresponding_widget_list_count=sound_events_holder.get_corresponding_list_count(obj))

                sound_events_holder.draw_all_instances(context, obj, layout)

                self.draw_events(obj, "script_events_list", 0.1, "Parameters (Frame Number/Script Xevt)",
                                 "Script Events",
                                 layout, parameters=["Frame", "Script Xevt"], corresponding_widget_list_count=
                                 script_events_holder.get_corresponding_list_count(obj))
                script_events_holder.draw_all_instances(context, obj, layout)


                self.draw_events(obj, "snap_events_list", 0.1, "Parameters (Frame Number/Actor/Translation/Quaternion)",
                                 "Snap Events", layout,
                                 parameters=["Frame", "Actor", "X", "Y", "Z", "QX", "QY", "QZ", "QW", ],
                                 corresponding_widget_list_count=snap_events_holder.get_corresponding_list_count(obj))

                snap_events_holder.draw_all_instances(context, obj, layout)

                self.draw_events(obj, "reaction_events_list", 0.1,
                                 "Parameters (Frame Number/Reaction ASM/Reaction State)",
                                 "Reaction Events", layout,
                                 parameters=["Frame", "Reaction ASM Name", "Reaction State Name"],
                                 corresponding_widget_list_count=reaction_events_holder.get_corresponding_list_count(obj))

                reaction_events_holder.draw_all_instances(context, obj, layout)

                self.draw_events(obj, "play_effect_events_list", 0.1,
                                 "Parameters (Frame Number/VFX Name/Actor Name/Bone Name/(always 0)/Target Actor Name/Target Bone Name/Unique VFX Name)",
                                 "Play Effect Events", layout,
                                 parameters=["Frame", "VFX Name", "Actor Name", "Bone Name", "(always 0)",
                                             "Target Actor Name", "Target Bone Name", "Unique VFX Name"],
                                 corresponding_widget_list_count=play_effect_events_holder.get_corresponding_list_count(obj))
                play_effect_events_holder.draw_all_instances(context, obj, layout)
                self.draw_events(obj, "stop_effect_events_list", 0.1,
                                 "Parameters (Frame Number/Unique VFX Name/(always 0)/Unknown Bool 1)",
                                 "Stop Effect Events", layout,
                                 parameters=["Frame", "Unique VFX Name", "(always 0)", "(unknown bool)"])
                self.draw_events(obj, "disable_lipsync_events_list", 0.1, "Parameters (Frame Number/Duration)",
                                 "Suppress Lipsync Events", layout, parameters=["Frame", "End Frame"])
                self.draw_events(obj, "visibility_events_list", 0.1, "Parameters (Frame Number/Actor/Visibility)",
                                 "Visibility Events", layout,
                                 parameters=["Frame", "Actor Name", "Visibility (0 or 1)"], corresponding_widget_list_count=len(obj.visibility_events_list_UI))
                visibility_events_holder.draw_all_instances(context, obj, layout)
                self.draw_events(obj, "focus_compatibility_events_list", 0.1, "Parameters (End Frame,Level)",
                                 "Focus Compatibility Events", layout)
                self.draw_events(obj, "geometry_state_change_events_list", 0.1, "Parameters (Frame/Actor Name/Geometry State Name)",
                                 "Geometry State Change Events", layout)
            layout.prop(obj, "show_experimental_options", text="Show Experimental Options")
            if obj.show_experimental_options:
                box = layout.box()
                box.prop(context.scene, "clip_locos", text="Clip Loco(s)")
                box.prop(obj, "reset_initial_offset_t", text="Reset Initial Offset T")
                box.prop(obj, "additional_snap_frames", text="Additional Snap Frames")
                box.prop(context.scene, "downsample_60_to_30", text="Downsample 60 fps to 30")
                if obj.is_actor:
                    if obj.actor_type == "sim":
                        # layout.prop(obj, "active_sim_skin", text="Active Sim Skin")
                        box.prop(obj, "allow_slots", text="Allow Modifying Slot Bone in Clip")

                box.prop(obj, "disable_rig_suffix", text="Disable Rig Suffix")
                box.prop(obj, "is_overlay", text="Is Overlay")

                box.prop(obj, "subroot_for_animations", text="Subroot for Animations (Import)")
                box.prop(obj, "insert_last_parent_event_to_start", text="Insert Last Parent Event To Start (Import)")
                box.operator("s4animtools.reset_slot_assignment_preview", text="Reset Slot Assignment Preview")

              #  box.label(text="Use Full Precision means using full precision for all animation data.")
              #  box.label(text="Don't enable if you don't know what that means! ")
              #  box.label(text="This will cause unnecessarily large file sizes and has a hard limit on how much animation data can be stored.")
              #  box.prop(obj, "use_full_precision", text="EXPERIMENTAL!! Use Full Precision")
              #  box.prop(obj, "use_world_bone_as_root",
              #           text="Use World Rig and Bone as Root for IK Targets on Object")
             #   box.label(text="The base rig is only used for additive animations such as the infant carrier from Growing Together.")
              # ## box.label(text="The base rig setting is not used for normal animations.")
               # box.prop_search(obj, "base_rig", context.scene, "objects", text="Base Rig")
               # box.label(text="Export an Additive Clip. Do not use for normal animations")
              #  box.operator("s4animtools.new_export_clip", icon='MESH_CUBE', text="Export Additive Clip").additive = True


                row = box.row()
                row.operator("s4animtools.mask_out_parents", text="Mask Out Parents")
                row.operator("s4animtools.mask_out_children", text="Mask Out Children")
               # layout.operator("s4animtools.create_finger_ik", icon='MESH_CUBE', text="Create Finger IK")
               # layout.operator("s4animtools.create_ik_rig", icon='MESH_CUBE', text="Create IK Rig")
            row =  layout.row()
            try:
                selected_bone = bpy.context.selected_pose_bones[0]

                self.layout.label(text=selected_bone.name)
                #for ik_idx in range(-1,11):
                #    row = self.layout.row()
                #    row.scale_x = 1
                #    if ik_idx == -1:
                #        row.prop(selected_bone, f"ik_pos_{ik_idx}", text=f"Pos")
                #        row.prop(selected_bone, f"ik_rot_{ik_idx}", text=f"Rot")
#
                #    else:
                #        row.prop(selected_bone, f"ik_pos_{ik_idx}", text=f"IK Pos {ik_idx}")
                #        row.prop(selected_bone, f"ik_rot_{ik_idx}", text=f"IK Rot {ik_idx}")
                #    row.scale_x = 2.5
                #    row.prop(selected_bone, f"ik_weight_{ik_idx}", text=f"IK Weight {ik_idx}")
#
            except Exception as e:
                pass



        else:
            layout.label(text="Select an object to get started.")

      #  self.layout.operator("s4animtools.add_new_locomotion_builder", text="Add New Locomotion Builder")
      #  self.layout.operator("s4animtools.read_locomotion_builder_from_folder", text="Read Locomotion Builder From Folder Extracted By S4S")
      #
      #  draw_locomotion_builder_data(self.layout, context)
    def draw_all_ik_targets_of_type(self, context, obj, row, chain_bone):
        excluded = ["b__L_Hand__", "b__R_Hand__", "b__L_Foot__", "b__R_Foot__", "b__ROOT_bind__"]
        box = row.column()
        box.label(text=f"{chain_bone}")
        ik_chain_count = 0
        for idx, item in enumerate(get_ik_targets(obj)):
            if item.chain_bone == chain_bone:
                ik_chain_count += 1


       # print(ik_chain_count, chain_bone)
        current_chain_idx = 0
        for idx, item in enumerate(get_ik_targets(obj)):
            if chain_bone == "":
                if item.chain_bone not in excluded:
                    self.draw_ik_target(context, current_chain_idx, item, obj, box, ik_chain_count)
                    current_chain_idx += 1

            elif item.chain_bone == chain_bone:

                self.draw_ik_target(context, current_chain_idx, item, obj, box, ik_chain_count)
                current_chain_idx += 1
        return row

    def draw_ik_target(self, context, idx, item, obj, row, ik_chain_count):
        sub = row.row()
        #sub = row.row()
        actual_idx = -1
        for new_idx, ik_target in enumerate(obj.ik_targets):
            if ik_target == item:
                actual_idx = new_idx
        sub.label(text=f"IK Target #{get_ik_target_idx_for_slot_assignment_on_chain(obj, item)}")
        sub.scale_x = 1

      #  sub.prop(item, "chain_idx", text="Chain")

      #  sub.scale_x = 0.5
        sub.operator('iktarget.delete_specific', text='Delete').command = str(actual_idx)
        #print(idx, ik_chain_count, item.chain_bone)
        if idx == ik_chain_count - 1:
            sub.operator('iktarget.new', text='Clone').command = f"{item.chain_bone}"
        row = row.box()
        sub = row.row(align=True)
        sub.operator("s4animtools.preview_slot_assignment", text= "Preview Slot Assignment").command = str(actual_idx)
        sub = row.row(align=True)
        sub.prop_search(item, "chain_bone", obj.pose, "bones")
        sub = row.row(align=True)
        try:
            sub.prop_search(item, "target_obj", context.scene, "objects")
            sub = row.row(align=True)

            if item.target_obj !=  "":
                target_obj = bpy.data.objects[item.target_obj]
                sub.prop_search(item, "target_bone", target_obj.pose, "bones")
                if item.target_bone == "":
                    sub.operator('s4animtools.guesstarget', text="Guess").command = "{},{}".format(item.chain_bone, item.target_obj)

        except:
            pass

        for range_idx, range in enumerate(item.ranges):
            sub = row.row(align=True)

            sub.prop(range, "start_time", text="Start")
            sub.prop(range, "end_time", text="End")
            sub.operator('iktarget.delete_ik_range', text="Delete").command = f"{actual_idx},{range_idx}"

        row.operator('iktarget.new_ik_range', text="New Range").command = str(actual_idx)
        return row





class QuaternionConfig(PropertyGroup):
    w: bpy.props.FloatProperty(default=1.0)
    x: bpy.props.FloatProperty(default=0.0)
    y: bpy.props.FloatProperty(default=0.0)
    z: bpy.props.FloatProperty(default=0.0)


class PositionConfig(PropertyGroup):
    w: bpy.props.FloatProperty(default=0.0)
    y: bpy.props.FloatProperty(default=0.0)
    z: bpy.props.FloatProperty(default=0.0)


class ActorSettings(PropertyGroup):
    # Export the animation for this actor
    actor_enabled: BoolProperty(default=True)
    initial_offset_quaternion: bpy.props.PointerProperty(type=QuaternionConfig)
    initial_offset_position: bpy.props.PointerProperty(type=PositionConfig)


class S4ANIMTOOLS_OT_move_new_element(bpy.types.Operator):
    bl_idname = "s4animtools.move_new_element"
    bl_label = ""
    bl_options = {"REGISTER", "UNDO"}

    args: StringProperty()

    def execute(self, context):
        obj = context.object
        args = self.args.split(',')
        list_to_edit, idx, operation = args[0], int(args[1]), args[2]
        to_edit = getattr(obj, list_to_edit)
        new_data = ""
        elements = []
        for element in to_edit:
            elements.append(element.info)
        if operation == "up" or operation == "down":
            new_data = elements[idx]
        if operation == "up" and idx == 0:
            return {"FINISHED"}
        elif operation == "down" and idx == len(to_edit) - 1:
            return {"FINISHED"}

        if operation == "up":
            new_list = [*elements[0:idx - 1], new_data, elements[idx - 1], *elements[idx + 1:]]
        elif operation == "down":
            new_list = [*elements[0:idx], elements[idx + 1], new_data, *elements[idx + 2:]]
        elif operation == "delete":
            new_list = [*elements[0:idx], *elements[idx + 1:]]
        elif operation == "create":
            new_list = [*elements[0:idx + 1], new_data, *elements[idx + 1:]]

        to_edit.clear()
        self.readd_elements(new_list, to_edit)

        return {"FINISHED"}

    def readd_elements(self, elements_to_append, to_edit):
        for i, element in enumerate(elements_to_append):
            to_edit.add()
            to_edit[-1].info = element
           # print(f'adding {element}')


class ClipData(PropertyGroup):
    clip_name: StringProperty()
    referenced_actors: StringProperty()
    clip_display_name: StringProperty()

    clip_description: StringProperty()
    start_frame: IntProperty(name="Start", description="Start Frame",
                            default=0, min=0)
    end_frame: IntProperty(name="End", description="End Frame",
                          default=0, min=0)
    additional_snap_frames : CollectionProperty(type=IntProperty)
    clip_loco : BoolProperty()

class s4animtool_PT_IKTargetPanel(bpy.types.Panel):
    """Create the IK Event Panel"""
    bl_label = "IK Targets"
    bl_idname = "OBJECT_PT_ik_targets_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout


class ImportRig(bpy.types.Operator, ImportHelper):
    bl_idname = "s4animtools.import_rig"
    bl_label = "Import Rig"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        create_rig_with_context(self.properties.filepath, context)

        return {"FINISHED"}

class OT_S4ANIMTOOLS_ApplyTrackmask(bpy.types.Operator, ImportHelper):
    bl_idname = "s4animtools.apply_trackmask"
    bl_label = "Apply Trackmask"
    bl_options = {"REGISTER", "UNDO"}

    def copy_location(self, arm, target, from_target, influence):
        print(f"Copying position from {target.name} to {from_target.name}")
        copy_constraint = from_target.constraints.new('COPY_LOCATION')
        copy_constraint.target = arm
        copy_constraint.subtarget = target.name
        copy_constraint.influence = influence
        copy_constraint.target_space = 'LOCAL'
        copy_constraint.owner_space = 'LOCAL'

        return copy_constraint

    def copy_rotation(self, arm, target, from_target, influence):
        print(f"Copying position from {target.name} to {from_target.name}")
        copy_constraint = from_target.constraints.new('COPY_ROTATION')
        copy_constraint.target = arm
        copy_constraint.subtarget = target.name
        copy_constraint.influence = influence

        copy_constraint.target_space = 'LOCAL'
        copy_constraint.owner_space = 'LOCAL'


        return copy_constraint

    def execute(self, context):
        trackmask = Trackmask().read(self.properties.filepath)
        arm = context.object
        base_arm = bpy.data.objects[context.object.name.replace("_blended", "_base")]
        human_bones = s4animtools.bone_names.human_bones
        for bone in arm.pose.bones:
            if bone.name in human_bones:
                for c in bone.constraints:
                    bone.constraints.remove(c)
                self.copy_location(base_arm, base_arm.pose.bones[bone.name], bone,  1 - trackmask.track_blends[human_bones.index(bone.name)])
                self.copy_rotation(base_arm, base_arm.pose.bones[bone.name], bone, 1 - trackmask.track_blends[human_bones.index(bone.name)])

        return {"FINISHED"}

class InitializeEvents(bpy.types.Operator):
    bl_idname = "s4animtools.initialize_events"
    bl_label = "Initialize Events"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if len(context.object.parent_events_list) == 0:
            context.object.parent_events_list.add()
        if len(context.object.sound_events_list) == 0:
            context.object.sound_events_list.add()
        if len(context.object.script_events_list) == 0:
            context.object.script_events_list.add()
        if len(context.object.play_effect_events_list) == 0:
            context.object.play_effect_events_list.add()
        if len(context.object.stop_effect_events_list) == 0:
            context.object.stop_effect_events_list.add()
        if len(context.object.disable_lipsync_events_list) == 0:
            context.object.disable_lipsync_events_list.add()
        if len(context.object.snap_events_list) == 0:
            context.object.snap_events_list.add()
        if len(context.object.reaction_events_list) == 0:
            context.object.reaction_events_list.add()
        if len(context.object.visibility_events_list) == 0:
            context.object.visibility_events_list.add()
        if len(context.object.focus_compatibility_events_list) == 0:
            context.object.focus_compatibility_events_list.add()
        if len(context.object.geometry_state_change_events_list) == 0:
            context.object.geometry_state_change_events_list.add()
        return {"FINISHED"}


class OT_S4ANIMTOOLS_AddSoundEventsListUI(bpy.types.Operator):
    bl_idname = "s4animtools.add_sound_events_list_ui"
    bl_label = "Add Events"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if len(context.object.sound_events_list_UI) == 0:
            context.object.sound_events_list_UI.add()
        return {"FINISHED"}

class OT_S4ANIMTOOLS_AddScriptEventsListUI(bpy.types.Operator):
    bl_idname = "s4animtools.add_sound_events_list_ui"
    bl_label = "Add Events"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if len(context.object.script_events_list_UI) == 0:
            context.object.script_events_list_UI.add()
        return {"FINISHED"}

class OT_S4ANIMTOOLS_UpgradeData(bpy.types.Operator):
    bl_idname = "s4animtools.upgrade_data"
    bl_label = "upgrade_data"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        handle_version_upgrade(context)
        return {"FINISHED"}
def get_offset(source_obj, source_root, target_obj, target_bone):
    object_matrix = target_obj.matrix_world @ target_bone.matrix
    actor_matrix = source_obj.matrix_world @ source_root.matrix
    offset = object_matrix.inverted() @ actor_matrix

    rotation = offset.to_quaternion()
    translation = offset.to_translation()

    return translation, rotation
def format_offset_to_list(translation, rotation):
    translation_list = [translation[0],translation[1],translation[2]]
    rotation_list = [rotation[1], rotation[2], rotation[3] ,rotation[0]]
    return translation_list, rotation_list

def update_initial_offsets(self, context):
    active_object_root = context.active_object.pose.bones["b__ROOT__"]
    if context.object.relative_rig == "":
        relative_rig = context.active_object
        relative_bone = None
    else:
        relative_rig = bpy.data.objects[context.object.relative_rig]
        relative_bone = relative_rig.pose.bones[context.object.relative_bone]

    translation, rotation = get_offset(context.active_object, active_object_root, relative_rig, relative_bone)
    # It bothered me far too much to have the height sticking out of the ground or under the ground.
    # This shouldn't actually do anything in game, just for my own sanity.

    initial_offset_height = round(translation[1], 4)
    if abs(round(translation[1], 4)) < 0.01:
        initial_offset_height = 0
    context.active_object.initial_offset_q = ",".join(
        [str(round(rotation[1], 4)), str(round(rotation[2], 4)), str(round(rotation[3], 4)),
         str(round(rotation[0], 4))])
    context.active_object.initial_offset_t = ",".join(
        [str(round(translation[0], 4)), str(initial_offset_height), str(round(translation[2], 4))])

    return  None

class MaintainKeyframe(bpy.types.Operator):
    bl_idname = "s4animtools.maintain_keyframe"
    bl_label = "Import Rig"
    bl_options = {"REGISTER", "UNDO"}

    direction: bpy.props.EnumProperty(items=(('FORWARDS', 'FORWARDS', ""), ('BACK', 'BACK', ""),))

    def execute(self, context):
        active_object = context.active_object
        selected_bone = context.selected_pose_bones[0]

        matrix_data = selected_bone.matrix.copy()
        #print(matrix_data)
        if self.direction == "FORWARDS":
            bpy.context.scene.frame_set(context.scene.frame_current + 1)
        else:
            bpy.context.scene.frame_set(context.scene.frame_current - 1)

        selected_bone.matrix = matrix_data
        selected_bone.keyframe_insert(data_path="location", frame=context.scene.frame_current)
        selected_bone.keyframe_insert(data_path="rotation_quaternion", frame=context.scene.frame_current)

        return {"FINISHED"}


class ExportAnimationStateMachine(bpy.types.Operator):
    bl_idname = "s4animtools.export_animation_state_machine"
    bl_label = "ExportAnimationStateMachine"
    bl_options = {"REGISTER", "UNDO"}

    def create_actor(self, actor_name, actor_type, is_master, is_virtual):
        actor_status = f'<Actor name="{actor_name}" type="{actor_type}" master="{str(is_master).lower()}" virtual="{str(is_virtual).lower()}" />'
        if actor_type == "Sim":
            actor_status += f'<Parameter name="x:age" type="enum" labels="baby,toddler,child,teen,youngadult,adult,elder" default="adult" />' \
                            f'<Parameter name="x:sex" type="enum" labels="male,female" default="male" />' \
                            f'<Parameter name="x:mood" type="enum" labels="happy,confident,angry,sad,bored,embarrassed,uncomfortable,playful,tense,focused,energized,flirty,fine,inspired,dazed" default="happy" />'
        return actor_status

    def create_posture_manifest(self, actor_name, posture_name, posture_family, compatibility, carry_left, carry_right,
                                surface):
        if posture_family == "":
            posture_family = "none"
        posture_manifest = f'<PostureManifest actors="{actor_name}">' \
                           f'<Support name="{posture_name}" family="{posture_family}" compatibility="{compatibility}" carry_left="{carry_left}" carry_right="{carry_right}" surface="{surface}" />' \
                           f'</PostureManifest>'
        return posture_manifest

    def create_state_connections(self, prev, next):
        text = f'<Connection from="{prev}" to="{next}" />'
        return text

    def create_controller(self, clip_name, target, focus, mask, track, blendin, blendout):
        text = f'<Controller target="{target}" controller="@ClipController(clip={clip_name}_{target}, loop_count=#1)" overridePosture="false" mask="{mask}" track="{track}" mirror_conditional="False" suppress_footsteps="False" transition_class_in="Default" transition_class_out="Default" ik_configuration="a2o_singingSkill_singInShower.ma" focus="{str(focus).lower()}" start_frame_offset="0" end_frame_offset="0" timescale="1" unique_id="{self.unique_id}">' \
               f'<TransitionClassList><Transition transition_class_name="Default" transition_duration_in="{round(blendin, 3)}" use_custom_transition_in="true" transition_type_in="linear" transition_mask_in="" transition_duration_out="{round(blendout, 3)}" use_custom_transition_out="false" transition_type_out="linear" transition_mask_out="" /></TransitionClassList></Controller>'

        return text

    def create_state(self, name, type, skippable, focus, facial_overlay, controllers, interrupt_this):
        is_public = "public"

        if not type:
            is_public = "private"

        text = f'<State name="{name}" type="{is_public}" skippable="{str(skippable).lower()}" interrupt_this="{str(interrupt_this).lower()}" focus="{str(focus).lower()}"  facialoverlays="{str(facial_overlay).lower()}" tailoverlays="true">'
        for controller in controllers:
            text += self.create_controller(controller.name, controller.target, controller.focus, controller.mask,
                                           controller.track, controller.blendin, controller.blendout)
        text += "</State>"
        return text

    def create_state_header(self, name, type, skippable, focus, facial_overlay, controllers, interrupt_this):
        is_public = "public"

        if not type:
            is_public = "private"

        text = f'<State name="{name}" type="{is_public}" skippable="{str(skippable).lower()}" interrupt_this="{str(interrupt_this).lower()}" focus="{str(focus).lower()}"  facialoverlays="{str(facial_overlay).lower()}" tailoverlays="true"/>'
        return text

    def execute(self, context):
        import xml.dom.minidom

        self.unique_id = 1

        anim_path = os.path.join(os.path.expanduser("~/Desktop"), "Animation Workspace",
                                 "02D5DF13!00000000!" + get_64bithash(
                                     context.object.name.lower()) + "." + context.object.name + ".AnimationStateMachine")
        text = '<?xml version="1.0" encoding="utf-8"?>' \
               f'<ASM name="{context.object.name}" dcc="sage">'
        for actor in context.object.actors:
            text += self.create_actor(actor.name, actor.type, actor.master, actor.virtual)
        for actor in context.object.postures:
            text += self.create_posture_manifest(actor.actor1, actor.posture_name, actor.posture_family,
                                                 actor.compatibility, actor.carry_left, actor.carry_left, actor.surface)
        for state in context.object.states:
            text += self.create_state_header(state.name, state.public, state.skippable, state.focus,
                                             state.facial_overlays, state.controllers, state.interrupt_this)
        for connection in context.object.state_connections:
            text += self.create_state_connections(connection.previous_state, connection.next_state)
        for state in context.object.states:
            text += self.create_state(state.name, state.public, state.skippable, state.focus, state.facial_overlays,
                                      state.controllers, state.interrupt_this)
        text += "</ASM>"
        dom = xml.dom.minidom.parseString(text)  # or xml.dom.minidom.parseString(xml_string)
        pretty_xml_as_string = dom.toprettyxml()

        with open(anim_path, "w") as file:
            file.write(pretty_xml_as_string)

        return {"FINISHED"}


class OT_S4ANIMTOOLS_CreateBoneSelectors(bpy.types.Operator):
    bl_idname = "s4animtools.create_bone_selectors"
    bl_label = "Create Bone Selectors"
    bl_options = {"REGISTER", "UNDO"}

    def select_bone_group(self, obj, bone_group_name):
        if bone_group_name not in obj.pose.bone_groups:
            obj.pose.bone_groups.new(name=bone_group_name)
        obj.pose.bone_groups.active = obj.pose.bone_groups[bone_group_name]

    def get_index_of_bone_group(self, obj, bone_group_name):
        for idx, group in enumerate(obj.pose.bone_groups):
            if group.name == bone_group_name:
                return idx
        return -1

    def assign_bones_to_group_if_match(self, obj, match_fn, bone_group_name):
        for bone in obj.pose.bones:
            if match_fn(bone):
                setattr(bone, bone_group_name, True)
                print(f"Selecting {bone.name} for {bone_group_name}")
            else:
                setattr(bone, bone_group_name, False)


    def execute(self, context):
        obj = context.object

        while len(obj.pose.bone_groups) > 0:
            bpy.ops.pose.group_remove()

      #  self.assign_bones_to_group_if_match(obj, is_slot_bone, "is_slot")
      #  self.assign_bones_to_group_if_match(obj, is_cas_bone, "is_cas")
      #  self.assign_bones_to_group_if_match(obj, is_left_bone, "is_left")
      #  self.assign_bones_to_group_if_match(obj, is_right_bone, "is_right")
      #  self.assign_bones_to_group_if_match(obj, is_left_pinky_bone, "is_left_pinky")
      #  self.assign_bones_to_group_if_match(obj, is_left_ring_bone, "is_left_ring")
      #  self.assign_bones_to_group_if_match(obj, is_left_mid_bone, "is_left_middle")
      #  self.assign_bones_to_group_if_match(obj, is_left_index_bone, "is_left_index")
      #  self.assign_bones_to_group_if_match(obj, is_left_thumb_bone, "is_left_thumb")
      #  self.assign_bones_to_group_if_match(obj, is_first_left_finger_joint, "is_left_first_finger")
      #  self.assign_bones_to_group_if_match(obj, is_second_left_finger_joint, "is_left_second_finger")
      #  self.assign_bones_to_group_if_match(obj, is_third_left_finger_joint, "is_left_third_finger")
      #  self.assign_bones_to_group_if_match(obj, is_right_finger_joint, "is_right_finger")
      #  self.assign_bones_to_group_if_match(obj, is_right_pinky_bone, "is_right_pinky")
      #  self.assign_bones_to_group_if_match(obj, is_right_ring_bone, "is_right_ring")
      #  self.assign_bones_to_group_if_match(obj, is_right_mid_bone, "is_right_middle")
      #  self.assign_bones_to_group_if_match(obj, is_right_index_bone, "is_right_index")
      #  self.assign_bones_to_group_if_match(obj, is_right_thumb_bone, "is_right_thumb")
      #  self.assign_bones_to_group_if_match(obj, is_first_right_finger_joint, "is_right_first_finger")
      #  self.assign_bones_to_group_if_match(obj, is_second_right_finger_joint, "is_right_second_finger")
      #  self.assign_bones_to_group_if_match(obj, is_third_right_finger_joint, "is_right_third_finger")
      #  self.assign_bones_to_group_if_match(obj, is_right_finger_joint, "#")
      #  self.assign_bones_to_group_if_match(obj, is_middle_bone, "is_middle")
      #  self.assign_bones_to_group_if_match(obj, is_mouth, "is_mouth")


        return {"FINISHED"}

class OT_S4ANIMTOOLS_CreateFingerIK(bpy.types.Operator):
    bl_idname = "s4animtools.create_finger_ik"
    bl_label = "Create Bone Selectors"
    bl_options = {"REGISTER", "UNDO"}

    def create_ik_constraint(self, from_target):
        ik_constraint = from_target.constraints.new('IK')
        ik_constraint.chain_count = 3
        return ik_constraint


    def execute(self, context):
        obj = context.object

        for bone in obj.pose.bones:
            if is_third_right_finger_joint(bone) or is_third_left_finger_joint(bone):
                self.create_ik_constraint(bone)
        return {"FINISHED"}

class OT_S4ANIMTOOLS_CreateIKRig(bpy.types.Operator):
    bl_idname = "s4animtools.create_ik_rig"
    bl_label = "Create IK Rig"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        arm = context.object.data
        bones_with_ik_targets = ["b__L_Hand__", "b__R_Hand__", "b__L_Foot__", "b__R_Foot__"]
        ik_targets_to_poles = {"b__L_Hand__": "b__L_ArmExportPole__",
                               "b__R_Hand__": "b__R_ArmExportPole__",
                               "b__L_Foot__": "b__L_LegExportPole__",
                               "b__R_Foot__": "b__R_LegExportPole__",
                               }
        reset_parents = ["b__L_LegExportPole__", "b__R_LegExportPole__"]

        hold = "Hold"
        ik = "IK"

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        edit_bones = arm.edit_bones[:]
        for b in edit_bones:
            if b.name in reset_parents:
                if b.parent.name != "b__Pelvis__":
                    for b2 in edit_bones:
                        if b2.name == "b__ROOT__":
                            b.parent = b2

        for b in edit_bones:
            if "Hold" in b.name:
                arm.edit_bones.remove(b)
            elif "IK" in b.name:
                arm.edit_bones.remove(b)

        edit_bones = arm.edit_bones[:]

        for b in edit_bones:
            if b.name in bones_with_ik_targets:
                print(b.name)

                cb = arm.edit_bones.new(b.name + hold)
                cb.head = b.head
                cb.tail = b.tail
                cb.matrix = b.matrix
                cb.parent = b.parent

                cb = arm.edit_bones.new(b.name + ik)
                cb.parent = arm.edit_bones["b__ROOT__"]

                cb.head = b.head
                cb.tail = b.tail
                cb.head = Vector((0, 0, 0))
                cb.tail = Vector((0, 0.1, 0))
                cb.matrix = b.matrix

        bpy.ops.object.mode_set(mode='POSE', toggle=False)
        arm = bpy.context.object
        for possible_IK_target in bones_with_ik_targets:
            if possible_IK_target + hold in arm.pose.bones:
                bone = arm.pose.bones[possible_IK_target + hold]
                ik_constraint = bone.constraints.new('IK')
                ik_constraint.target = arm
                ik_constraint.subtarget = possible_IK_target + ik
                ik_constraint.use_rotation = False
                ik_constraint.pole_target = arm
                ik_constraint.pole_subtarget = ik_targets_to_poles[possible_IK_target]
                ik_constraint.chain_count = 3
            if possible_IK_target in arm.pose.bones:
                bone = arm.pose.bones[possible_IK_target]
                copyrot_constraint = bone.constraints.new('COPY_ROTATION')
                copyrot_constraint.target = arm
                copyrot_constraint.subtarget = possible_IK_target + ik

        return {"FINISHED"}

class OT_S4ANIMTOOLS_SelectExportDirectory(bpy.types.Operator):
    bl_idname = "s4animtools.select_export_path"
    bl_label = "Select Export Path"
    bl_options = {'REGISTER'}

    directory: StringProperty(
        name="Outdir Path")

    def execute(self, context):
        bpy.context.scene.s4animtools_export_path = self.directory
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class OT_S4ANIMTOOLS_DetermineBalance(bpy.types.Operator):
    bl_idname = "s4animtools.determine_balance"
    bl_label = "determine_balance"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """
        This code checks the balance of the character.
        Balance is defined as the ability to support one's self using their feet.
        To determine balance, we find the midpoint of the feet.
        Then, we check how far the hips are from that midpoint.
        If the hips are within a certain distance, we consider the character balanced.
        This is used in Pose Mode.
        """
        obj = context.object
        hips = obj.pose.bones["b__ROOT_bind__"]
        left_foot = obj.pose.bones["b__L_Foot__"]
        right_foot = obj.pose.bones["b__R_Foot__"]
        head = obj.pose.bones["b__Head__"]

        for frame in range(context.scene.frame_start, context.scene.frame_end):
            context.scene.frame_set(frame)
            pos = left_foot.matrix.to_translation() + right_foot.matrix.to_translation()
            # Project pelvis to floor (0 position)
            midpoint = Vector((pos.x / 2, 0, pos.z / 2))
            hips_pos = hips.matrix.to_translation()
            hips_pos.z = 0

            head_pos = head.matrix.to_translation()
            #print(head_pos)
            head_pos.z = 0

            head_plus_hips = hips_pos + head_pos
            head_plus_hips_midpoint = Vector((head_plus_hips.x / 2, head_plus_hips.y / 2, 0))
            hips_cost = ( hips_pos- midpoint).length * 1
            spine_cost = (head_plus_hips_midpoint - midpoint).length * 1
            balance = spine_cost# + spine_cost
            print(hips_pos, head_plus_hips_midpoint, midpoint)
            print(hips_cost, spine_cost)
            obj.balance = balance
            obj.keyframe_insert(data_path="balance", frame=frame)
            obj.pose.bones["Offset"].matrix = Matrix.LocRotScale(midpoint, None, None)
            obj.pose.bones["Offset"].keyframe_insert(data_path="location", frame=frame)

        return {"FINISHED"}

class OT_S4ANIMTOOLS_MaskOutParents(bpy.types.Operator):
    bl_idname = "s4animtools.mask_out_parents"
    bl_label = "Mask Out Parents"
    bl_options = {"REGISTER", "UNDO"}
    command: StringProperty()


    def get_all_parents(self, bone):
        all_parents = []
        parent = bone
        while parent is not None:
            parent = parent.parent
            if parent is not None:
                all_parents.append(parent)
        all_parents = list(reversed(all_parents))
        return all_parents


    def get_shared_direct_parent(self, bone1, bone2):
        parents1 = self.get_all_parents(bone1)
        parents2 = self.get_all_parents(bone2)
        # if len(parents1) == len(parents2):
        # if parents1[-1] == parents2[-1]:
        #    print(parents1[-1], parents2[-1], bone1, bone2)
        #     return True
        if len(parents1) > len(parents2):
            if bone2 in parents1:
                return True

        return False

    def execute(self, context):
        obj = context.object

        if len(context.selected_pose_bones_from_active_object) > 0:
            active_pose_bone = context.selected_pose_bones_from_active_object[0]

            possible_paths = ['pose.bones["{}"].location', 'pose.bones["{}"].rotation_euler',
                              'pose.bones["{}"].rotation_quaternion']

            bones_to_enable = [active_pose_bone]
            bones_to_disable = []
            all_pose_bones = obj.pose.bones
            for bone in all_pose_bones:
                if self.get_shared_direct_parent(bone, active_pose_bone):
                    bones_to_enable.append(bone)

            # for bone in bones_to_enable:
            # print(bone.name)
            for bone in all_pose_bones:
                # print(bone.name)
                for possible_path in possible_paths:
                    possible_formatted_path = possible_path.format(bone.name)
                    for fcurve in obj.animation_data.action.fcurves:
                        if fcurve.data_path == possible_formatted_path:
                            fcurve.mute = bone not in bones_to_enable
        return {"FINISHED"}

class OT_S4ANIMTOOLS_MaskOutChildren(bpy.types.Operator):
    bl_idname = "s4animtools.mask_out_children"
    bl_label = "Mask Out Children"
    bl_options = {"REGISTER", "UNDO"}
    command: StringProperty()


    def get_all_parents(self, bone):
        all_parents = []
        parent = bone
        while parent is not None:
            parent = parent.parent
            if parent is not None:
                all_parents.append(parent)
        all_parents = list(reversed(all_parents))
        return all_parents


    def get_shared_direct_parent(self, bone1, bone2):
        parents1 = self.get_all_parents(bone1)
        parents2 = self.get_all_parents(bone2)
        # if len(parents1) == len(parents2):
        # if parents1[-1] == parents2[-1]:
        #    print(parents1[-1], parents2[-1], bone1, bone2)
        #     return True
        if bone2 in parents1:
            return False

        return True

    def execute(self, context):
        obj = context.object

        if len(context.selected_pose_bones_from_active_object) > 0:
            active_pose_bone = context.selected_pose_bones_from_active_object[0]

            possible_paths = ['pose.bones["{}"].location', 'pose.bones["{}"].rotation_euler',
                              'pose.bones["{}"].rotation_quaternion']

            bones_to_enable = [active_pose_bone]
            bones_to_disable = []
            all_pose_bones = obj.pose.bones
            for bone in all_pose_bones:
                if self.get_shared_direct_parent(bone, active_pose_bone):
                    bones_to_enable.append(bone)

            # for bone in bones_to_enable:
            # print(bone.name)
            for bone in all_pose_bones:
                # print(bone.name)
                for possible_path in possible_paths:
                    possible_formatted_path = possible_path.format(bone.name)
                    for fcurve in obj.animation_data.action.fcurves:
                        if fcurve.data_path == possible_formatted_path:
                            fcurve.mute = bone not in bones_to_enable
        return {"FINISHED"}

class OT_S4ANIMTOOLS_ToggleSlots(bpy.types.Operator):
    bl_idname = "s4animtools.toggle_slots"
    bl_label = "Toggle Slots"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not hasattr(context.object, "pose"):
            return {"CANCELLED"}
        if not hasattr(context.object.pose, "bones"):
            return {"CANCELLED"}
        # The current count of slot bones that are enabled
        visible_slot_bones = 0
        # The current count of slot bones that are hidden
        invisible_slot_bones = 0
        for bone in context.object.pose.bones:
            if bone.name.endswith("_slot"):
                if not bone.bone.hide:
                    visible_slot_bones += 1
                else:
                    invisible_slot_bones += 1
        # If most bones are visible, assume that the user wants to hide them,
        # otherwise, show all of them
        if visible_slot_bones > invisible_slot_bones:
            for bone in context.object.pose.bones:
                if bone.name.endswith("_slot"):
                    bone.bone.hide = True
        else:
            for bone in context.object.pose.bones:
                if bone.name.endswith("_slot"):
                    bone.bone.hide = False

        return {"FINISHED"}


class OT_S4ANIMTOOLS_ResetSlotAssignmentPreview(bpy.types.Operator):
    bl_idname = "s4animtools.reset_slot_assignment_preview"
    bl_label = "Toggle Slots"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        for obj in context.scene.objects:
            if hasattr(obj, "pose"):
                if hasattr(obj.pose, "bones"):
                    for bone in obj.pose.bones:
                        if bone.name.startswith("ik_bone_"):
                            # Delete the constraints from the bone to make it ready for use in another anim
                            for constraint in bone.constraints:
                                if constraint.name.startswith("IK Child Of"):
                                    bone.constraints.remove(constraint)
                        if bone.name in ["L.FootTarget.IK", "R.FootTarget.IK"] or \
                            bone.name in ["L.HandTarget.IK", "R.HandTarget.IK"] or \
                            bone.name == "b__ROOT_bind__":
                            for constraint in bone.constraints:
                                constraint.driver_remove("influence")
                                if constraint.name.startswith("IK Copy Location") or constraint.name.startswith("IK Copy Rotation"):
                                    bone.constraints.remove(constraint)


        return {"FINISHED"}


classes = (
    Snapper, ExportRig, SyncRigToMesh,
    S4ANIMTOOLS_PT_MainPanel,
    TimeRange,
    IKTarget, s4animtool_PT_IKTargetPanel, LIST_OT_NewIKTarget, LIST_OT_CreateIKTarget, LIST_OT_DeleteIKTarget, LIST_OT_MoveIKTarget,
    s4animtool_OT_bakeik, s4animtool_OT_removeIK, s4animtools_OT_guessTarget,
    BeginIKMarker, s4animtool_OT_unmute_ik, s4animtool_OT_mute_ik, NewClipExporter, PositionConfig, QuaternionConfig,
    ActorSettings, ClipData, ImportRig, CopyLeftSideAnimationToRightSide, CopyLeftSideAnimationToRightSideSim, CopyBakedAnimationToControlRig,
    CopySelectedLeftSideToRightSide, ExportAnimationStateMachine, MaintainKeyframe, AnimationEvent, InitializeEvents,
    S4ANIMTOOLS_OT_move_new_element, AnimationEvent,
    LIST_OT_NewIKRange, LIST_OT_DeleteIKRange, LIST_OT_DeleteSpecificIKTarget, FlipLeftSideAnimationToRightSideSim, OT_S4ANIMTOOLS_ImportFootprint, OT_S4ANIMTOOLS_ExportFootprint,
    OT_S4ANIMTOOLS_VisualizeFootprint, OT_S4ANIMTOOLS_CreateBoneSelectors, OT_S4ANIMTOOLS_CreateFingerIK, OT_S4ANIMTOOLS_CreateIKRig,
    OT_S4ANIMTOOLS_MaskOutParents, OT_S4ANIMTOOLS_ApplyTrackmask, OT_S4ANIMTOOLS_MaskOutChildren,
    S4ANIMTOOL_OT_ExportAllClips, OT_S4ANIMTOOLS_SelectExportDirectory,
    OT_S4ANIMTOOLS_AddSoundEventsListUI, OT_S4ANIMTOOLS_AddScriptEventsListUI,
    OT_S4ANIMTOOLS_UpgradeData,
    OT_S4ANIMTOOLS_NewExportClip,
    OT_S4ANIMTOOLS_ToggleSlots, OT_S4ANIMTOOLS_CreateClipData, OT_S4ANIMTOOLS_InitializeThumbnails, OT_S4ANIMTOOLS_PreviewSlotAssignment, OT_S4ANIMTOOLS_PreviewAllSlotAssignments,
    S4ANIMTOOLS_OT_DeleteAllIKTargets,S4ANIMTOOLS_OT_CreateIKChain, S4ANIMTOOLS_OT_CreateBones,S4ANIMTOOLS_OT_FKIKSwitch,S4ANIMTOOLS_OT_IKFKSwitch, S4ANIMTOOLS_OT_LoadPresetBoneConfig,
OT_S4ANIMTOOLS_ResetSlotAssignmentPreview)

def update_selected_bones(self, context):
    pass


def handle_version_upgrade(context):
    

    old_version = context.scene.s4animtools_version
    # This code handles upgrading the addon from an older version.

    # This portion handles updating from older versions of the code before the version var was added.
    # This always runs.

    for obj in context.scene.objects:
        if obj.is_s4_actor:
            if old_version < 2:
                obj.is_actor = obj.is_s4_actor
        if len(obj.sound_events_list) > 0:
            # Iterate through all sound events and upgrade them to the new format.
            for event in obj.sound_events_list:
                if event.info != "":
                    frame_number, sound_name = event.info.split(",")
                    obj.sound_events_list_UI.add()
                    obj.sound_events_list_UI[-1].frame_number = int(frame_number)
                    obj.sound_events_list_UI[-1].sound_name = sound_name
            obj.sound_events_list.clear()
        if len(obj.parent_events_list) > 0:
            for event in obj.parent_events_list:
                if event.info != "":
                    frame_number, child_actor, parent_actor, parent_bone = event.info.split(",")
                    obj.parent_events_list_UI.add()
                    obj.parent_events_list_UI[-1].frame_number = int(frame_number)
                    obj.parent_events_list_UI[-1].child_actor = child_actor
                    obj.parent_events_list_UI[-1].parent_actor = parent_actor
                    obj.parent_events_list_UI[-1].parent_bone = parent_bone
            obj.parent_events_list.clear()
        if len(obj.script_events_list) > 0:
            for event in obj.script_events_list:
                if event.info != "":
                    frame_number, event_id = event.info.split(",")
                    obj.script_events_list_UI.add()
                    obj.script_events_list_UI[-1].frame_number = int(frame_number)
                    obj.script_events_list_UI[-1].event_id = int(event_id)
            obj.script_events_list.clear()
        if len(obj.reaction_events_list) > 0:
            for event in obj.reaction_events_list:
                if event.info != "":
                    frame_number, reaction_asm, reaction_state = event.info.split(",")
                    obj.reaction_events_list_UI.add()
                    obj.reaction_events_list_UI[-1].frame_number  = int(frame_number)

                    obj.reaction_events_list_UI[-1].reaction_asm  = reaction_asm
                    obj.reaction_events_list_UI[-1].reaction_state = reaction_state
            obj.reaction_events_list.clear()

        if len(obj.play_effect_events_list) > 0:
            for event in obj.play_effect_events_list:
                if event.info != "":
                    try:
                        frame_number, vfx_name, actor_name, bone_name, always_zero, target_actor_name, target_bone_name, unique_vfx_name = event.info.split(",")
                    except ValueError:
                        # Earlier versions didn't support target_actor_name and target_bone_name and set it to the same value. Fill these with blank
                        frame_number, vfx_name, actor_name, bone_name, always_zero, always_zero_2, unique_vfx_name = event.info.split(",")
                        target_actor_name = ""
                        target_bone_name = ""
                    obj.play_effect_events_list_UI.add()
                    obj.play_effect_events_list_UI[-1].frame_number  = int(frame_number)

                    obj.play_effect_events_list_UI[-1].vfx_name  = vfx_name
                    obj.play_effect_events_list_UI[-1].actor  = actor_name
                    obj.play_effect_events_list_UI[-1].bone  = bone_name
                    obj.play_effect_events_list_UI[-1].always_zero  = int(always_zero)

                    obj.play_effect_events_list_UI[-1].target_actor  = target_actor_name
                    obj.play_effect_events_list_UI[-1].target_bone  = target_bone_name
                    obj.play_effect_events_list_UI[-1].unique_vfx_name  = unique_vfx_name
            obj.play_effect_events_list.clear()

        if len(obj.visibility_events_list) > 0:
            for event in obj.visibility_events_list:
                if event.info != "":
                    frame_number, actor_name, visibility = event.info.split(",")
                    obj.visibility_events_list_UI.add()
                    obj.visibility_events_list_UI[-1].frame_number  = int(frame_number)

                    obj.visibility_events_list_UI[-1].actor  = actor_name
                    obj.visibility_events_list_UI[-1].visibility  = visibility == str(1)
            obj.visibility_events_list.clear()
    context.scene.s4animtools_version = CURRENT_S4ANIMTOOLS_VERSION

def register_footprint_properties():
    # Tons of footprint related stuff
    bpy.types.Object.is_footprint = BoolProperty(default=False)

    bpy.types.Object.for_placement = BoolProperty(default=False)
    bpy.types.Object.for_pathing = BoolProperty(default=False)
    bpy.types.Object.is_enabled = BoolProperty(default=False)
    bpy.types.Object.discouraged = BoolProperty(default=False)
    bpy.types.Object.landing_strip = BoolProperty(default=False)
    bpy.types.Object.no_raycast = BoolProperty(default=False)
    bpy.types.Object.placement_slotted = BoolProperty(default=False)
    bpy.types.Object.encouraged = BoolProperty(default=False)
    bpy.types.Object.terrain_cutout = BoolProperty(default=False)

    bpy.types.Object.is_routing_footprint = BoolProperty(default=False)

    bpy.types.Object.slope = BoolProperty(default=False)
    bpy.types.Object.outside = BoolProperty(default=False)
    bpy.types.Object.inside = BoolProperty(default=False)

    bpy.types.Object.terrain = BoolProperty(default=False)
    bpy.types.Object.floor = BoolProperty(default=False)
    bpy.types.Object.pool = BoolProperty(default=False)
    bpy.types.Object.pond = BoolProperty(default=False)
    bpy.types.Object.fence_post = BoolProperty(default=False)
    bpy.types.Object.any_surface = BoolProperty(default=False)
    bpy.types.Object.air = BoolProperty(default=False)
    bpy.types.Object.roof = BoolProperty(default=False)

    bpy.types.Object.is_none = BoolProperty(default=False)
    bpy.types.Object.is_walls = BoolProperty(default=False)
    bpy.types.Object.is_objects = BoolProperty(default=False)
    bpy.types.Object.is_sims = BoolProperty(default=False)
    bpy.types.Object.is_roofs = BoolProperty(default=False)
    bpy.types.Object.is_fences = BoolProperty(default=False)
    bpy.types.Object.is_modular_stairs = BoolProperty(default=False)
    bpy.types.Object.is_objects_of_same_type = BoolProperty(default=False)
    bpy.types.Object.is_columns = BoolProperty(default=False)

    bpy.types.Object.is_reserved_space = BoolProperty(default=False)
    bpy.types.Object.is_foundations = BoolProperty(default=False)
    bpy.types.Object.is_fenestration_node = BoolProperty(default=False)
    bpy.types.Object.is_trim = BoolProperty(default=False)

    bpy.types.Object.ignores_none = BoolProperty(default=False)
    bpy.types.Object.ignores_walls = BoolProperty(default=False)
    bpy.types.Object.ignores_objects = BoolProperty(default=False)
    bpy.types.Object.ignores_sims = BoolProperty(default=False)
    bpy.types.Object.ignores_roofs = BoolProperty(default=False)
    bpy.types.Object.ignores_fences = BoolProperty(default=False)
    bpy.types.Object.ignores_modular_stairs = BoolProperty(default=False)
    bpy.types.Object.ignores_objects_of_same_type = BoolProperty(default=False)
    bpy.types.Object.ignores_columns = BoolProperty(default=False)

    bpy.types.Object.ignores_reserved_space = BoolProperty(default=False)
    bpy.types.Object.ignores_foundations = BoolProperty(default=False)
    bpy.types.Object.ignores_fenestration_node = BoolProperty(default=False)
    bpy.types.Object.ignores_trim = BoolProperty(default=False)

def unregister_footprint_properties():
    del bpy.types.Object.is_footprint
    del bpy.types.Object.for_placement
    del bpy.types.Object.for_pathing
    del bpy.types.Object.is_enabled
    del bpy.types.Object.discouraged
    del bpy.types.Object.landing_strip
    del bpy.types.Object.no_raycast
    del bpy.types.Object.placement_slotted
    del bpy.types.Object.encouraged
    del bpy.types.Object.terrain_cutout
    del bpy.types.Object.is_routing_footprint
    del bpy.types.Object.slope
    del bpy.types.Object.outside
    del bpy.types.Object.inside
    del bpy.types.Object.terrain
    del bpy.types.Object.floor
    del bpy.types.Object.pool
    del bpy.types.Object.pond
    del bpy.types.Object.fence_post
    del bpy.types.Object.any_surface
    del bpy.types.Object.air
    del bpy.types.Object.roof
    del bpy.types.Object.is_none
    del bpy.types.Object.is_walls
    del bpy.types.Object.is_objects
    del bpy.types.Object.is_sims
    del bpy.types.Object.is_roofs
    del bpy.types.Object.is_fences
    del bpy.types.Object.is_modular_stairs
    del bpy.types.Object.is_objects_of_same_type
    del bpy.types.Object.is_columns
    del bpy.types.Object.is_reserved_space
    del bpy.types.Object.is_foundations
    del bpy.types.Object.is_fenestration_node
    del bpy.types.Object.is_trim
    del bpy.types.Object.ignores_none
    del bpy.types.Object.ignores_walls
    del bpy.types.Object.ignores_objects
    del bpy.types.Object.ignores_sims
    del bpy.types.Object.ignores_roofs
    del bpy.types.Object.ignores_fences
    del bpy.types.Object.ignores_modular_stairs
    del bpy.types.Object.ignores_objects_of_same_type
    del bpy.types.Object.ignores_columns
    del bpy.types.Object.ignores_reserved_space
    del bpy.types.Object.ignores_foundations
    del bpy.types.Object.ignores_fenestration_node
    del bpy.types.Object.ignores_trim

def register():
    """Register classes for the things."""
    from bpy.utils import register_class
    locomotion_register()
    register_footprint_properties()
    for event_holder in all_event_holders:
        try:
            event_holder.register_blender_class()
        except Exception as e:
            print(e)
    for cls in classes:
        try:
            register_class(cls)
        except Exception as e:
            print(e)
    bpy.types.PoseBone.mirrored_bone = StringProperty()
    bpy.types.PoseBone.bone_flags = StringProperty()

    # This is for the baked IK data
    for ik_idx in range(-1,11):
        setattr(bpy.types.PoseBone, f"ik_pos_{ik_idx}", bpy.props.FloatVectorProperty(size=3))
        setattr(bpy.types.PoseBone, f"ik_rot_{ik_idx}", bpy.props.FloatVectorProperty(default=(0,0,0,1), size=4, min=-1, max=1))
        setattr(bpy.types.PoseBone, f"ik_weight_{ik_idx}", bpy.props.FloatProperty(min=0, max=1))

    bpy.types.Object.balance = bpy.props.FloatProperty(default=0, soft_min=0, soft_max=1)


    # One for IK, zero for fk
    bpy.types.Object.l_hand_fk_ik = FloatProperty(default=0, soft_min=0, soft_max=1)
    bpy.types.Object.r_hand_fk_ik = FloatProperty(default=0, soft_min=0, soft_max=1)

    bpy.types.Object.l_foot_fk_ik = FloatProperty(default=0, soft_min=0, soft_max=1)
    bpy.types.Object.r_foot_fk_ik = FloatProperty(default=0, soft_min=0, soft_max=1)
    bpy.types.Object.disable_rig_suffix = BoolProperty(default=False)

    bpy.types.Object.parent_events_list = CollectionProperty(type=AnimationEvent)
    bpy.types.Object.sound_events_list = CollectionProperty(type=AnimationEvent)
    bpy.types.Object.script_events_list = CollectionProperty(type=AnimationEvent)
    bpy.types.Object.reaction_events_list = CollectionProperty(type=AnimationEvent)
    bpy.types.Object.play_effect_events_list = CollectionProperty(type=AnimationEvent)
    bpy.types.Object.stop_effect_events_list = CollectionProperty(type=AnimationEvent)
    bpy.types.Object.disable_lipsync_events_list = CollectionProperty(type=AnimationEvent)
    bpy.types.Object.snap_events_list = CollectionProperty(type=AnimationEvent)
    bpy.types.Object.visibility_events_list = CollectionProperty(type=AnimationEvent)
    bpy.types.Object.focus_compatibility_events_list = CollectionProperty(type=AnimationEvent)
    bpy.types.Object.geometry_state_change_events_list = CollectionProperty(type=AnimationEvent)

    bpy.types.Object.ik_targets = CollectionProperty(type=IKTarget)
    bpy.types.Object.ik_idx = IntProperty(default=0)

    bpy.types.Object.rig_name = StringProperty()
    bpy.types.Object.reset_initial_offset_t = StringProperty()
    bpy.types.Object.allow_jaw_animation_for_entire_animation = BoolProperty(default=False)
    bpy.types.Object.explicit_namespaces = StringProperty()
    bpy.types.Object.reference_namespace_hash = StringProperty()
    bpy.types.Object.initial_offset_q = StringProperty()
    bpy.types.Object.initial_offset_t = StringProperty()

    bpy.types.Object.snap_events = StringProperty()
    bpy.types.Object.additional_snap_frames = StringProperty()
    bpy.types.Object.visibility_events = StringProperty()

    bpy.types.Object.base_rig = StringProperty()
    bpy.types.Object.world_rig = StringProperty()
    bpy.types.Object.world_bone = StringProperty()
    bpy.types.Object.use_world_bone_as_root = BoolProperty(default=False)

    bpy.types.Object.relative_rig = StringProperty(update=update_initial_offsets)
    bpy.types.Object.relative_bone = StringProperty(update=update_initial_offsets)
    bpy.types.Object.use_full_precision = BoolProperty(default=False)

    # bpy.types.Object.script_idx = IntProperty(name="Index for my_list", default=0)
    # bpy.types.Object.sound_idx = IntProperty(name="Index for sound_idx", default=0)
    bpy.types.Object.actor_idx = IntProperty(name="Index for actors", default=0)
    bpy.types.Object.state_idx = IntProperty(name="Index for state", default=0)
    bpy.types.Object.controller_idx = IntProperty(name="Index for state", default=0)
    bpy.types.Object.posture_idx = IntProperty(name="Index for state", default=0)
    bpy.types.Object.state_connection_idx = IntProperty(name="Index for state", default=0)

    #  bpy.types.Object.clip_idx = IntProperty(name="Index for clip", default=0)
    bpy.types.Object.is_overlay = BoolProperty(default=False)

    bpy.types.Scene.watcher_running = BoolProperty(default=False)
    bpy.types.Scene.clip_name = StringProperty()
    bpy.types.Scene.clip_name_prefix = StringProperty()
    bpy.types.Scene.clip_splits = StringProperty()
    bpy.types.Scene.clip_locos = StringProperty()

    bpy.types.Object.footprint_name = StringProperty()

    bpy.types.Object.footprint_resource_variant = bpy.props.EnumProperty(
        # (identifier, name, description, icon, number)
        items=[('Regular Object', 'Regular Object', '', '', 0),
               ('World Camera Bounds', 'World Camera Bounds', '', '', 1),
               ('World Allowed Routing', 'World Allowed Routing', '', '', 2)],
        name="Footprint Type Variant",
        default='Regular Object')

    bpy.types.Scene.s4animtools_export_path = StringProperty()
    bpy.types.Scene.s4animtools_export_path2 = StringProperty()

    bpy.types.Scene.export_as_loose_files = BoolProperty()

    actor_types = (("sim", "Sim", "This actor is a sim."), ("object", "Object", "This actor is an object."), ("prop", "Prop", "This actor is a prop."))
    game_types = (("TS4", "TS4", "The Sims 4"),)#, ("TS3", "TS3", "The Sims 3"))

    # Deprecated, use is_actor instead.
    bpy.types.Object.is_s4_actor = BoolProperty(default=False)

    bpy.types.Object.is_actor = BoolProperty(default=False)
    # Actor type can be sim, object, or prop
    bpy.types.Object.actor_type = bpy.props.EnumProperty(items = actor_types)
    bpy.types.Object.game_type = bpy.props.EnumProperty(items = game_types)

    bpy.types.Object.is_enabled_for_animation = BoolProperty(default=False)
    bpy.types.Object.show_footprint_options = BoolProperty(default=False)
    bpy.types.Object.show_mirror_and_masking_options = BoolProperty(default=False)
    bpy.types.Object.show_control_rig_options = BoolProperty(default=False)
    bpy.types.Object.show_ik_options = BoolProperty(default=False)
    bpy.types.Object.show_events = BoolProperty(default=False)
    bpy.types.Object.show_clip_options = BoolProperty(default=False)
    bpy.types.Object.show_initial_offset_options = BoolProperty(default=False)

    bpy.types.Object.show_experimental_options = BoolProperty(default=False)
    bpy.types.Object.is_sim_skin = BoolProperty(default=False)

    bpy.types.Object.allow_slots = BoolProperty(default=False)

    # 60 FPS downsample to 30
    bpy.types.Scene.downsample_60_to_30 = BoolProperty(default=False)

    bpy.types.Scene.s4animtools_version = IntProperty(default=CURRENT_S4ANIMTOOLS_VERSION)

    bpy.types.Scene.clips = CollectionProperty(type=ClipData)

    bpy.types.Scene.pose_pack_mode_enabled = BoolProperty(default=False)
    bpy.types.Object.animation_notes = StringProperty()

    bpy.types.Scene.use_picker_ui = BoolProperty(default=False)
    bpy.types.Object.insert_last_parent_event_to_start = BoolProperty(default=False)
    bpy.types.Object.subroot_for_animations = bpy.props.IntProperty()

    # Bones to create IK chains for. Despite the name
    # these are the FK
    bpy.types.Object.original_bone_01 = bpy.props.StringProperty()
    bpy.types.Object.original_bone_02 = bpy.props.StringProperty()
    bpy.types.Object.original_bone_03 = bpy.props.StringProperty()

    bpy.types.Object.original_bone_04 = bpy.props.StringProperty()

    bpy.types.Object.ik_bone_01_fk_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_02_fk_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_03_fk_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_01_ik_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_02_ik_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_03_ik_name = bpy.props.StringProperty()

    bpy.types.Object.original_bone_11 = bpy.props.StringProperty()
    bpy.types.Object.original_bone_12 = bpy.props.StringProperty()
    bpy.types.Object.original_bone_13 = bpy.props.StringProperty()
    bpy.types.Object.original_bone_14 = bpy.props.StringProperty()

    bpy.types.Object.ik_bone_11_fk_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_12_fk_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_13_fk_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_11_ik_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_12_ik_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_13_ik_name = bpy.props.StringProperty()

    # The bone at the end of the IK chain, same level as IK Bone 3 (Hand), but its main purpose is to
    # actually store the IK constraint. (IK Bone 3 has the *final* rotation for the hand)
    bpy.types.Object.ik_bone_04_ik_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_14_ik_name = bpy.props.StringProperty()

    # The target bone for the IK chain. This bone has no parent.
    bpy.types.Object.ik_bone_05_ik_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_15_ik_name = bpy.props.StringProperty()

    # The IK Chain pole
    bpy.types.Object.ik_bone_06_ik_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_16_ik_name = bpy.props.StringProperty()

    # The IK pole indicator
    bpy.types.Object.ik_bone_07_ik_name = bpy.props.StringProperty()
    bpy.types.Object.ik_bone_17_ik_name = bpy.props.StringProperty()
    # Whether IK is enabled for this IK Chain. 0 = disabled, 1 = enabled
    # Values inbetween are possible, but why.
    bpy.types.Object.left_arm_ik_enabled = bpy.props.FloatProperty(name="Left Arm IK Enabled", soft_min=0, soft_max=1,
                                                                   min=0, max=1)
    bpy.types.Object.right_arm_ik_enabled = bpy.props.FloatProperty(name="Right Arm IK Enabled", soft_min=0, soft_max=1,
                                                                    min=0, max=1)
    bpy.types.Object.left_leg_ik_enabled = bpy.props.FloatProperty(name="Left Leg IK Enabled", soft_min=0, soft_max=1,
                                                                   min=0, max=1)
    bpy.types.Object.right_leg_ik_enabled = bpy.props.FloatProperty(name="Right Leg IK Enabled", soft_min=0, soft_max=1,
                                                                    min=0, max=1)
    bpy.types.Object.baked_eye_animation_enabled = bpy.props.FloatProperty(name="Baked Eye Animation Enabled",
                                                                           soft_min=0, soft_max=1, min=0, max=1,
                                                                           default=1)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        try:
            unregister_class(cls)
        except:
            pass

    unregister_footprint_properties()
    for ik_idx in range(-1, 11):
        pos, rot = getattr(bpy.types.PoseBone, f"ik_pos_{ik_idx}"), getattr(bpy.types.PoseBone, f"ik_rot_{ik_idx}")
        del pos
        del rot

    del bpy.types.Object.l_hand_fk_ik
    del bpy.types.Object.r_hand_fk_ik
    del bpy.types.Object.l_foot_fk_ik
    del bpy.types.Object.r_foot_fk_ik
    del bpy.types.Object.disable_rig_suffix


    del bpy.types.Object.parent_events_list
    del bpy.types.Object.sound_events_list
    del bpy.types.Object.script_events_list
    del bpy.types.Object.reaction_events_list
    del bpy.types.Object.play_effect_events_list
    del bpy.types.Object.stop_effect_events_list
    del bpy.types.Object.disable_lipsync_events_list
    del bpy.types.Object.snap_events_list
    del bpy.types.Object.focus_compatibility_events_list
    del bpy.types.Object.geometry_state_change_events_list


    del bpy.types.Object.ik_targets
    del bpy.types.Object.ik_idx

    del bpy.types.Object.rig_name
    del bpy.types.Object.reset_initial_offset_t
    del bpy.types.Object.allow_jaw_animation_for_entire_animation
    del bpy.types.Object.explicit_namespaces
    del bpy.types.Object.reference_namespace_hash
    del bpy.types.Object.initial_offset_q
    del bpy.types.Object.initial_offset_t

    del bpy.types.Object.snap_events
    del bpy.types.Object.additional_snap_frames
    del bpy.types.Object.visibility_events

    del bpy.types.Object.base_rig
    del bpy.types.Object.world_rig
    del bpy.types.Object.world_bone
    del bpy.types.Object.use_world_bone_as_root

    del bpy.types.Object.relative_rig
    del bpy.types.Object.relative_bone
    del bpy.types.Object.use_full_precision

    del bpy.types.Object.actor_idx
    del bpy.types.Object.state_idx
    del bpy.types.Object.controller_idx
    del bpy.types.Object.posture_idx
    del bpy.types.Object.state_connection_idx

    del bpy.types.Object.is_overlay

    del bpy.types.Scene.watcher_running
    del bpy.types.Scene.clip_name
    del bpy.types.Scene.clip_name_prefix
    del bpy.types.Scene.clip_splits
    del bpy.types.Scene.clip_locos

    del bpy.types.Object.footprint_name
    del bpy.types.Object.footprint_resource_variant

    del bpy.types.Scene.s4animtools_export_path
    del bpy.types.Scene.s4animtools_export_path2

    del bpy.types.Scene.export_as_loose_files

    del bpy.types.Object.is_actor
    del bpy.types.Object.actor_type
    del bpy.types.Object.is_enabled_for_animation
    del bpy.types.Object.show_footprint_options
    del bpy.types.Object.show_mirror_and_masking_options
    del bpy.types.Object.show_control_rig_options
    del bpy.types.Object.show_ik_options
    del bpy.types.Object.show_events
    del bpy.types.Object.show_clip_options
    del bpy.types.Object.show_initial_offset_options
    del bpy.types.Object.show_experimental_options
    del bpy.types.Object.is_sim_skin
    del bpy.types.Object.active_sim_skin

    del bpy.types.Object.allow_slots

    del bpy.types.Scene.downsample_60_to_30
    del bpy.types.Scene.s4animtools_version
    del bpy.types.Scene.clips
    del bpy.types.Scene.pose_pack_mode_enabled

    del bpy.types.Object.animation_notes
    del bpy.types.Scene.use_picker_ui

    del bpy.types.Object.insert_last_parent_event_to_start
    del bpy.types.Object.subroot_for_animations
    locomotion_unregister()

    for event_holder in all_event_holders:
        event_holder.unregister_blender_class()

    del bpy.types.Object.original_bone_01
    del bpy.types.Object.original_bone_02
    del bpy.types.Object.original_bone_03
    del bpy.types.Object.original_bone_04
    del bpy.types.Object.ik_bone_01_fk_name
    del bpy.types.Object.ik_bone_02_fk_name
    del bpy.types.Object.ik_bone_03_fk_name
    del bpy.types.Object.ik_bone_01_ik_name
    del bpy.types.Object.ik_bone_02_ik_name
    del bpy.types.Object.ik_bone_03_ik_name
    del bpy.types.Object.ik_bone_04_ik_name
    del bpy.types.Object.ik_bone_05_ik_name

    del bpy.types.Object.ik_bone_11
    del bpy.types.Object.ik_bone_12
    del bpy.types.Object.ik_bone_13
    del bpy.types.Object.ik_bone_11_fk_name
    del bpy.types.Object.ik_bone_12_fk_name
    del bpy.types.Object.ik_bone_13_fk_name
    del bpy.types.Object.ik_bone_11_ik_name
    del bpy.types.Object.ik_bone_12_ik_name
    del bpy.types.Object.ik_bone_13_ik_name
    del bpy.types.Object.ik_bone_14_ik_name
    del bpy.types.Object.ik_bone_15_ik_name

    del bpy.types.Object.ik_bone_06_ik_name
    del bpy.types.Object.ik_bone_16_ik_name

    del bpy.types.Object.ik_bone_07_ik_name
    del bpy.types.Object.ik_bone_17_ik_name

    del bpy.types.Object.left_arm_ik_enabled
    del bpy.types.Object.right_arm_ik_enabled
    del bpy.types.Object.left_leg_ik_enabled
    del bpy.types.Object.right_leg_ik_enabled