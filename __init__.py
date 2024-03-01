import bpy
import os
import time
import math
import importlib

import _s4animtools.bone_names
from _s4animtools.serialization.fnv import get_64bithash, get_32bit_hash
from _s4animtools.rcol.rcol_wrapper import OT_S4ANIMTOOLS_ImportFootprint, OT_S4ANIMTOOLS_VisualizeFootprint, \
    OT_S4ANIMTOOLS_ExportFootprint
from _s4animtools.rig.create_rig import Trackmask
from _s4animtools.rig_tools import ExportRig, SyncRigToMesh
from _s4animtools.events.events import SnapEvent, SoundEvent, ScriptEvent, ReactionEvent, VisibilityEvent, ParentEvent, \
    PlayEffectEvent, FocusCompatibilityEvent, SuppressLipsyncEvent, StopEffectEvent
from _s4animtools.serialization.types.basic import Float32, UInt32
from _s4animtools.clip_processing.clip_header import ClipResource, bone_to_slot_offset_idx
from _s4animtools.ik_baker import s4animtool_OT_bakeik, get_ik_targets

from _s4animtools.rig.create_rig import create_rig_with_context
import _s4animtools.clip_processing.clip_header
import _s4animtools.rig
import _s4animtools.channels.f1_normalized_channel
import _s4animtools.channels.translation_channel
import _s4animtools.channels.loco_channel
import _s4animtools.channels.palette_channel
import _s4animtools.channels.quaternion_channel
import _s4animtools.control_rig.basic_control_rig
import _s4animtools.frames.frame
from _s4animtools.control_rig.basic_control_rig import CopyLeftSideAnimationToRightSide, \
    CopySelectedLeftSideToRightSide, CopyLeftSideAnimationToRightSideSim, CopyBakedAnimationToControlRig, FlipLeftSideAnimationToRightSideSim
from _s4animtools.ik_manager import BeginIKMarker, LIST_OT_NewIKTarget,LIST_OT_CreateIKTarget, LIST_OT_DeleteIKTarget, LIST_OT_MoveIKTarget, \
    s4animtool_OT_removeIK, s4animtool_OT_mute_ik, s4animtool_OT_unmute_ik, LIST_OT_NewIKRange, LIST_OT_DeleteIKRange, \
    LIST_OT_DeleteSpecificIKTarget, MAX_SUBROOTS, s4animtools_OT_guessTarget
import _s4animtools.animation_exporter.animation
from _s4animtools.animation_exporter.animation import AnimationExporter, AdditiveAnimationExporter
import _s4animtools.rig.create_rig
from _s4animtools.serialization.types.transforms import Vector3, Quaternion4
import _s4animtools.clip_processing.clip_body
import _s4animtools.clip_processing.f1_palette
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector, Quaternion, Matrix
from bpy.props import IntProperty, CollectionProperty, FloatProperty
from bpy.types import PropertyGroup
from collections import defaultdict
JAW_ANIMATE_DURATION = 100000

CHAIN_STR_IDX = 2
bl_info = {"name": "_s4animtools", "category": "Object", "blender": (2, 80, 0)}



def update_valid_skins(scene, context):

    items = []

    for ob in context.scene.objects:
        if ob.is_sim_skin:
            items.append((ob.name, ob.name, ""))

    return items
def update_active_sim_skin(self, context):
    """
    Function for updating the active sim skin.
    This function copies over the rig from the active sim skin to the current rig.
    Note! Exported rigs do not have bones in our control rig, so for example the
    Left Hand IK and Right Hand IK need to be copied over from the hands default position.
    The feet need to be recreated as well.
    """
    rig_obj = context.object
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')

    if rig_obj.is_s4_actor:
        for child in bpy.data.objects[rig_obj.name].children:
            #print(rig_obj.name, child.name)
            child.select_set(True)
        bpy.ops.object.delete()

        new_skin = rig_obj.active_sim_skin
        bpy.ops.object.select_all(action='DESELECT')

        new_skin_rig = bpy.data.objects[new_skin]
        new_skin_rig.users_collection[0].hide_viewport = False
        new_skin_rig.select_set(True)

        bpy.ops.object.mode_set(mode='EDIT')
        bone_data = {}
        for bone in new_skin_rig.data.bones:
            print(bone.name)
            bone_data[bone.name] = (bone.head_local.copy(), bone.tail_local.copy())
            if bone.name == "b__L_Hand__":
                bone_data["Left Hand IK"] = (bone.head_local.copy(), bone.tail_local.copy())
                bone_data["Left Hand Target"] = (bone.head_local.copy(), bone.tail_local.copy())
            elif bone.name == "b__R_Hand__":
                bone_data["Right Hand IK"] = (bone.head_local.copy(), bone.tail_local.copy())
                bone_data["Right Hand Target"] = (bone.head_local.copy(), bone.tail_local.copy())
            elif bone.name == "b__L_Foot__":
                bone_data["Left Foot IK"] = (bone.head_local.copy(), bone.tail_local.copy())
                bone_data["Left Foot Target"] = (bone.head_local.copy(), bone.tail_local.copy())
                bone_data["Left Foot Main Parent"] = (bone.head_local.copy(), bone.tail_local.copy())
                bone_data["Left Foot Pivot"] = (bone.head_local.copy(), bone.tail_local.copy())
                bone_data["Left Foot Parent"] = (bone.head_local.copy(), bone.tail_local.copy())
            elif bone.name == "b__R_Foot__":
                bone_data["Right Foot IK"] = (bone.head_local.copy(), bone.tail_local.copy())
                bone_data["Right Foot Target"] = (bone.head_local.copy(), bone.tail_local.copy())
                bone_data["Right Foot Main Parent"] = (bone.head_local.copy(), bone.tail_local.copy())
                bone_data["Right Foot Pivot"] = (bone.head_local.copy(), bone.tail_local.copy())
                bone_data["Right Foot Parent"] = (bone.head_local.copy(), bone.tail_local.copy())
        bpy.ops.object.mode_set(mode='OBJECT')
        rig_obj.select_set(True)

        bpy.ops.object.mode_set(mode='EDIT')
        for bone in rig_obj.data.edit_bones:
            #print(bone.name)
            if bone.name in bone_data:
                bone.head = bone_data[bone.name][0]
                bone.tail = bone_data[bone.name][1]
                print(bone.name, bone_data[bone.name][0], bone_data[bone.name][1])

        bpy.ops.object.mode_set(mode='OBJECT')

        for child in new_skin_rig.children:
            new_ob = child.copy()
            bpy.context.scene.collection.objects.link(new_ob)
            print(rig_obj.name)
            new_ob.parent = bpy.data.objects[rig_obj.name]
            for modifier in new_ob.modifiers:
                print(modifier)
                if modifier.type == "ARMATURE":
                    modifier.object = bpy.data.objects[rig_obj.name]
        rig_obj.select_set(True)

        new_skin_rig.users_collection[0].hide_viewport = True

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
    f1normalized_channel = _s4animtools.channels.f1_normalized_channel.F1Normalized(bone_name, 5, 14 + sequence_count)
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
    f1normalized_channel = _s4animtools.channels.f1_normalized_channel.F1Normalized(bone_name, 5, 14)
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

    def modal(self, context, event):
        self.execute(context)

        if event.type == 'ESC':
            context.scene.watcher_running = False
            print("Giving up.")
            return {'FINISHED'}
        print("pass through")
        # all other events pass through to blender
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        run_as_modal = True
        print("Invoke me pls")
        if run_as_modal:
            self.timer = context.window_manager.event_timer_add(0.01, window=context.window)

            # set the monitoring property to True
            context.scene.watcher_running = True
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
            # run self to spawn cubes
        return {'FINISHED'}



class ClipInfo:
    def __init__(self, start_frame, end_frame, name, reference_namespace_hash, explicit_namespaces, initial_offset_q,
                 initial_offset_t, rig_name):
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


class SlotAssignmentBlender:
    def __init__(self, source_rig, source_bone, target_rig, target_bone, slot_assignment_idx, chain_idx):
        self.source_rig = source_rig
        self.source_bone = source_bone
        self.target_rig = target_rig
        self.target_bone = target_bone
        self.slot_assignment_idx = slot_assignment_idx
        self.chain_idx = chain_idx

class NewClipExporter(bpy.types.Operator):
    bl_idname = "s4animtools.new_export_clip"
    bl_label = "New Export Clip"
    bl_options = {"REGISTER", "UNDO"}

    additive: bpy.props.BoolProperty(default=False)
    def __init__(self):
        self.context = None
        self.clip_infos = []

    def setup_events(self, context, current_clip, start_frame, frame_count, additional_snap_frames):
        """Shifts the timestamps of the clip events depending on the split.
        So you can time it relative to the start of the blend file in blender,
        and have it reflect relative to the clip file in the export.
        """
        start_time = start_frame * (1 / 30)
        frame_time = frame_count * (1 / 30)
        variable_to_event = {context.object.parent_events_list: ParentEvent,
                             context.object.sound_events_list: SoundEvent,
                             context.object.snap_events_list: SnapEvent,
                             context.object.visibility_events_list: VisibilityEvent,
                             context.object.script_events_list: ScriptEvent,
                             context.object.reaction_events_list: ReactionEvent,
                             context.object.play_effect_events_list: PlayEffectEvent,
                             context.object.focus_compatibility_events_list: FocusCompatibilityEvent,
                             context.object.disable_lipsync_events_list: SuppressLipsyncEvent,
                             context.object.stop_effect_events_list: StopEffectEvent}
        snap_frames = []

        for parameter_fields, event in variable_to_event.items():
            for event_instance in parameter_fields:
                parameters = event_instance.info.split(",")
                parameter_length = len(parameters)
                if parameter_length == 1:
                    continue
                if parameter_length < event.arg_count:
                    raise Exception(
                        f"Your event has incomplete parameters. Expected {event.arg_count} parameters. Got {parameter_length}")
                original_timestamp = parameters[0].strip()
                if original_timestamp.startswith("//"):
                    continue
                original_timestamp, timeshifted_timestamp = self.create_timeshifted_timestamp(original_timestamp,
                                                                                              start_time)
                if event == SnapEvent:
                    if frame_time >= timeshifted_timestamp >= 0:

                        snap_frames.append(math.floor(timeshifted_timestamp * 30))
                        current_clip.add_event(event(timeshifted_timestamp, *parameters[1:]))

                elif event == FocusCompatibilityEvent:
                    if frame_time >= timeshifted_timestamp >= 0:
                        _, timeshifted_end_timestamp = self.create_timeshifted_timestamp(parameters[1].strip(),
                                                                                         start_time)
                        current_clip.add_event(
                            event(timeshifted_timestamp, timeshifted_end_timestamp, *parameters[2:]))
                elif event == SuppressLipsyncEvent:
                    if frame_time >= timeshifted_timestamp >= 0:
                        _, timeshifted_end_timestamp = self.create_timeshifted_timestamp(parameters[1].strip(),
                                                                                         start_time)
                        current_clip.add_event(
                            event(timeshifted_timestamp, timeshifted_end_timestamp, *parameters[2:]))
                else:
                    if frame_time >= timeshifted_timestamp >= 0:
                        current_clip.add_event(event(timeshifted_timestamp, *parameters[1:]))
        if context.object.allow_jaw_animation_for_entire_animation:
            current_clip.add_event(SuppressLipsyncEvent(0, JAW_ANIMATE_DURATION))
#                    raise Exception("You're missing parameters for your event..")

        if additional_snap_frames != "":
            additional_snap_frames = additional_snap_frames.split(",")
            for frame in additional_snap_frames:
                original_frame = int(frame)
                timeshifted_frame = original_frame - start_frame
                if frame_count > timeshifted_frame >= 0:
                    snap_frames.append(timeshifted_frame)
        return snap_frames

    def create_timeshifted_timestamp(self, original_timestamp_str, start_time):
        if original_timestamp_str.endswith("s"):
            original_timestamp = float(original_timestamp_str[:-1])
        elif original_timestamp_str.endswith("e"):
            original_timestamp = float(eval(original_timestamp_str[:-1]))
        elif original_timestamp_str.endswith("f"):
            original_timestamp = float(original_timestamp_str[:-1]) / 30
        else:
            original_timestamp = float(original_timestamp_str) / 30

        # What is relative mode???
       # # IF it ends with r (relative), then we don't need to shift from absolute to relative,
       # # because we're already in relative
       # if original_timestamp_str.endswith("r") and original_timestamp_str.endswith("rf"):
       #     timeshifted_timestamp = original_timestamp
       # else:
        timeshifted_timestamp = original_timestamp - start_time

        return original_timestamp, timeshifted_timestamp
    def get_clip_names(self):
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

    def get_clip_splits(self):
        clip_indices = [0, ]
        clip_splits = self.context.scene.clip_splits.split(",")
        # If the clip splits string is of zero length, then the user hasn't entered anything and needs to enter it.
        if len(self.context.scene.clip_splits) == 0:
            raise Exception("You need to specify clip splits")

        elif len(clip_splits) > 0:
            for split in clip_splits:
                clip_indices.append(int(split))
        return clip_indices

    def get_explicit_namespaces(self):
        return self.context.object.explicit_namespaces

    def get_reference_namespace_hash(self):
        return self.context.object.reference_namespace_hash

    def get_clip_infos(self):
        rig_name = self.context.object.rig_name
        if rig_name == "":
            raise Exception("You need to specify a rig name")
            return
        initial_offset_t = self.context.object.initial_offset_t
        initial_offset_q = self.context.object.initial_offset_q
        # Set the initial offsets to the default if the user doesn't enter anything.
        if initial_offset_t == "":
            initial_offset_t = "0,0,0"
        if initial_offset_q == "":
            initial_offset_q = "0,0,0,1"
        if len(self.clip_infos) == 0:
            clip_infos = []
            clip_names = self.get_clip_names()
            clip_indices = self.get_clip_splits()
            if len(clip_names) != len(clip_indices) - 1:
                raise ValueError(
                    "Clip names doesn't match clip indices. Please check your splits and names are the same length.")
            for clip_idx in range(len(clip_names)):
                clip_infos.append(
                    ClipInfo(start_frame=clip_indices[clip_idx], end_frame=clip_indices[clip_idx + 1], name=clip_names[clip_idx],
                             explicit_namespaces=self.get_explicit_namespaces(),
                             reference_namespace_hash=self.get_reference_namespace_hash(),
                             initial_offset_q=Quaternion4.from_str(initial_offset_q),
                             initial_offset_t=Vector3.from_str(initial_offset_t), rig_name=rig_name))
            self.clip_infos = clip_infos
        return self.clip_infos

    def get_downsampled_frame_idx(self, frame, sampling_rate):
        if sampling_rate == 1:
            return frame
        return frame // sampling_rate
    def execute(self, context):
        t1 = time.time()
        self.context = context
        self.clip_infos = []

        # Check if the user has toggled 60 fps downsampling to 30 fps
        if self.context.scene.downsample_60_to_30:
            if bpy.context.scene.render.fps != 60:
                raise ValueError("You need to set your render settings to 60 fps to downsample to 30.")



        source_filename = bpy.data.filepath.split(os.sep)[-1]
        ik_targets_to_bone = determine_ik_slot_targets(self.context.active_object)

        self.clip_infos = self.get_clip_infos()

        world_rig = self.context.object.world_rig
        world_root = self.context.object.world_bone

        if len(world_rig) == 0:
            world_rig = self.context.object
        else:
            world_rig = bpy.data.objects[world_rig]

        if len(world_root) == 0:
            world_root = world_rig.pose.bones["b__ROOT__"]
        else:
            world_root = world_rig.pose.bones[world_root]

        base_rig = self.context.object.base_rig


        for idx, clip_info in enumerate(self.clip_infos):
            current_clip = ClipResource(clip_info.name, clip_info.rig_name, ik_targets_to_bone,
                                        clip_info.explicit_namespaces,
                                        clip_info.reference_namespace_hash, clip_info.initial_offset_q,
                                        clip_info.initial_offset_t, source_filename, False, context.object.disable_rig_suffix)
            rig = self.context.object
            snap_frames = self.setup_events(self.context, current_clip, clip_info.start_frame, clip_info.end_frame - clip_info.start_frame,
                                            self.context.object.additional_snap_frames)

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

            # sampling rate. 1 for every frame, 2 for every other frame, etc.
            # Currently used for halving the animation data for 60 fps to 30 fps.
            sampling_rate = 1
            if self.context.scene.downsample_60_to_30:
                sampling_rate = 2

            # The +1 is for ensuring the last frame is included in the downsampled animation data.

            for frame_idx in range(clip_info.start_frame, clip_info.end_frame+1, sampling_rate):
                bpy.context.scene.frame_set(frame_idx)
                bpy.context.view_layer.update()
                exporter.animate_recursively(self.get_downsampled_frame_idx(frame_idx, sampling_rate), start_frame=self.get_downsampled_frame_idx(clip_info.start_frame, sampling_rate), force=frame_idx == clip_info.start_frame
                                                              or frame_idx == clip_info.end_frame)

                for source_bone_ik in slot_assignment_source_bones:
                    for ik_idx, slot_assignment_info in enumerate(ik_targets_to_bone[source_bone_ik]):

                        ik_weight = gather_ik_weights(rig, ik_weight_animation_data, slot_assignment_info.source_bone, ik_idx, self.get_downsampled_frame_idx(clip_info.start_frame, sampling_rate),
                                                      self.get_downsampled_frame_idx(frame_idx, sampling_rate), last_frame_influences[(slot_assignment_info.source_bone, ik_idx)])
                        last_frame_influences[(slot_assignment_info.source_bone, ik_idx)] = ik_weight

            for source_bone_ik in slot_assignment_source_bones:
                for ik_idx, slot_assignment_info in enumerate(ik_targets_to_bone[source_bone_ik]):
                    exporter.add_baked_animation_data_to_frame(slot_assignment_info.source_bone,
                                                               start_frame=self.get_downsampled_frame_idx(clip_info.start_frame, sampling_rate),
                                                               end_frame=self.get_downsampled_frame_idx(clip_info.end_frame, sampling_rate), ik_idx=ik_idx)
                    current_clip.clip_body.add_channel((create_ik_weight_channels(slot_assignment_info.source_bone, ik_weight_animation_data[(slot_assignment_info.source_bone, ik_idx)], ik_idx)))

            for channel in exporter.export_to_channels():
                current_clip.clip_body.add_channel(new_channel=channel)
            current_clip.clip_body.set_palette_values(exporter.paletteHolder.palette_values)
            current_clip.update_duration(self.get_downsampled_frame_idx(clip_info.end_frame, sampling_rate)- self.get_downsampled_frame_idx(clip_info.start_frame, sampling_rate))

            current_clip.export(export_path=self.context.scene.s4animtools_export_path)
        t2 = time.time()
        print(f"Took {t2 - t1} seconds for clip export")
        return {"FINISHED"}


class S4ANIMTOOL_OT_ExportAllClips(bpy.types.Operator):
    bl_idname = "s4animtools.export_all_clips"
    bl_label = "Export All Clips"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        for obj in bpy.data.objects:
            if obj.is_s4_actor and obj.is_enabled_for_animation:
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

    def draw_events(self, obj, events_list_name, x_scale, description, event_name, layout, parameters=None):
        events_list = getattr(obj, events_list_name)
        layout.label(
            text=f"{event_name}: {len(events_list)} - {description}")
        for idx, item in enumerate(events_list):
            row = layout.row()
            if item.info != "":
                if parameters is not None:
                    concat_string = ""
                    parameter_list = list(zip(parameters, item.info.split(",")))
                    for key, value in parameter_list:
                        layout.row().label(text=f"{key}: {value}")

                    for key in parameters[len(item.info.split(",") ):]:
                        layout.row().label(text=f"{key}: ?")
                    if len(parameters) > len(item.info.split(",")):
                        layout.row().label(text="Not enough parameters.")
                    if len(parameters) < len(item.info.split(",")):
                        layout.row().label(text="Too many parameters.")
                   # layout.row().label(text=concat_string[:-2])
            row2 = row.row()
            row.scale_x = x_scale

            row2.prop(item, "info", text="")


            row.operator('s4animtools.move_new_element', text='↑').args = f"{events_list_name},{idx},up"
            row.operator('s4animtools.move_new_element', text='↓').args = f"{events_list_name},{idx},down"
            row.operator('s4animtools.move_new_element', text='✖').args = f"{events_list_name},{idx},delete"
            row.operator('s4animtools.move_new_element', text='+').args = f"{events_list_name},{idx},create"
        layout.label(text="")

    def draw(self, context):
        obj = context.object

        layout = self.layout
        layout.operator("s4animtools.export_all_clips", icon="MESH_CUBE", text="Export All Clips")
        layout.prop(context.scene, "downsample_60_to_30",text="Downsample 60 fps to 30")
        if obj is not None:
            layout.prop(obj, "is_sim_skin", text="Is Sims 4 Skin")
            layout.prop(obj, "is_s4_actor", text="Is Sims 4 Actor")
            if obj.is_s4_actor:
                layout.prop(obj, "is_enabled_for_animation", text="Is Enabled for Animation")
                layout.prop(obj, "actor_type", text="Actor Type")
                if obj.actor_type == "sim":
                    layout.prop(obj, "active_sim_skin", text="Active Sim Skin")
                    layout.prop(obj, "allow_slots", text="Allow Slots")

            layout.prop(obj, "show_footprint_options", text="Show Footprint Options")
            if obj.show_footprint_options:
                layout.prop(obj, "is_footprint", text="Is Footprint Object")

                layout.operator("s4animtools.import_footprint", icon="MESH_CUBE", text="Import Footprint")
                layout.operator("s4animtools.export_footprint", icon="MESH_CUBE", text="Export Footprint")

                layout.operator("s4animtools.visualize_footprint", icon="MESH_CUBE", text="View Pathing Footprints").command="for_pathing"
                layout.operator("s4animtools.visualize_footprint", icon="MESH_CUBE", text="View Placement Footprints").command="for_placement"
                layout.operator("s4animtools.visualize_footprint", icon="MESH_CUBE", text="View Terrain Footprints").command="terrain"
                layout.operator("s4animtools.visualize_footprint", icon="MESH_CUBE", text="View Floor Footprints").command="floor"
                layout.operator("s4animtools.visualize_footprint", icon="MESH_CUBE", text="View Pool Footprints").command="pool"
                layout.prop(context.scene, "footprint_name", text="Footprint Name Or Hash")

                if obj.is_footprint:
                    layout = self.layout.row()
                    self.layout.label(text="Footprint is in: ")
                    layout = self.layout.row()

                    layout.prop(obj, "slope", text="Slope")
                    layout.prop(obj, "outside", text="Outside")
                    layout.prop(obj, "inside", text="Inside")

                    self.layout.label(text="Footprint is of Type: ")

                    layout = self.layout.row()
                    layout.prop(obj, "for_placement", text="For Placement")
                    layout.prop(obj, "for_pathing", text="For Pathing")
                    layout.prop(obj, "is_enabled", text="Is Enabled")
                    layout = self.layout.row()

                    layout.prop(obj, "discouraged", text="Discouraged")
                    layout.prop(obj, "landing_strip", text="Landing Strip")
                    layout.prop(obj, "no_raycast", text="No Raycast")
                    layout = self.layout.row()

                    layout.prop(obj, "placement_slotted", text="Placement Slotted")
                    layout.prop(obj, "encouraged", text="Encouraged")
                    layout.prop(obj, "terrain_cutout", text="Terrain Cutout")

                    self.layout.label(text="Footprint is of Surface Type: ")

                    layout = self.layout.row()
                    layout.prop(obj, "terrain", text="Terrain")
                    layout.prop(obj, "floor", text="Floor")
                    layout.prop(obj, "pool", text="Pool")
                    layout = self.layout.row()

                    layout.prop(obj, "pond", text="Pond")
                    layout.prop(obj, "fence_post", text="Fence Post")
                    layout.prop(obj, "any_surface", text="Any Surface")
                    layout = self.layout.row()

                    layout.prop(obj, "air", text="Air")
                    layout.prop(obj, "roof", text="Roof")

                    self.layout.label(text="Footprint Is Of Object Type: ")

                    layout = self.layout.row()
                    layout.prop(obj, "is_none", text="None")
                    layout.prop(obj, "is_walls", text="Walls")
                    layout.prop(obj, "is_objects", text="Objects")

                    layout = self.layout.row()
                    layout.prop(obj, "is_sims", text="Sims")
                    layout.prop(obj, "is_roofs", text="Roof")
                    layout.prop(obj, "is_fences", text="Fence")
                    layout = self.layout.row()

                    layout.prop(obj, "is_modular_stairs", text="Modular Stairs")
                    layout.prop(obj, "is_objects_of_same_type", text="Objects of Same Type")
                    layout.prop(obj, "is_columns", text="Columns")

                    layout = self.layout.row()
                    layout.prop(obj, "is_reserved_space", text="Reserved Space")

                    layout.prop(obj, "is_foundations", text="Foundations")
                    layout.prop(obj, "is_fenestration_node", text="Fenestration Node")
                    layout.prop(obj, "is_trim", text="Trim")

                    self.layout.label(text="Footprint Ignores Footprints of Object Type: ")

                    layout = self.layout.row()
                    layout.prop(obj, "ignores_none", text="None")
                    layout.prop(obj, "ignores_walls", text="Walls")
                    layout.prop(obj, "ignores_objects", text="Objects")

                    layout = self.layout.row()
                    layout.prop(obj, "ignores_sims", text="Sims")

                    layout.prop(obj, "ignores_roofs", text="Roof")
                    layout.prop(obj, "ignores_fences", text="Fence")
                    layout = self.layout.row()
                    layout.prop(obj, "ignores_modular_stairs", text="Modular Stairs")
                    layout.prop(obj, "ignores_objects_of_same_type", text="Objects of Same Type")
                    layout.prop(obj, "ignores_columns", text="Columns")

                    layout = self.layout.row()
                    layout.prop(obj, "ignores_reserved_space", text="Reserved Space")

                    layout.prop(obj, "ignores_foundations", text="Foundations")

                    layout.prop(obj, "ignores_fenestration_node", text="Fenestration Node")
                    layout.prop(obj, "ignores_trim", text="Trim")
            layout.prop(obj, "show_mirror_and_masking_options", text="Show Mirror/Mask/Maintain/Bake Options")

            if obj.show_mirror_and_masking_options:
                layout.operator("s4animtools.mask_out_parents", icon='MESH_CUBE', text="Mask Out Parents")
                layout.operator("s4animtools.mask_out_children", icon='MESH_CUBE', text="Mask Out Children")
                # Trackmasks are not working yet
                #layout.operator("s4animtools.apply_trackmask", icon='MESH_CUBE', text="Apply Trackmask")
                # self.layout.operator("s4animtools.copy_left_side", icon='MESH_CUBE', text="Copy Left Side (Bed)")
                layout.operator("s4animtools.flip_left_side_sim", icon='MESH_CUBE', text="Flip Sim")
                layout.operator("s4animtools.copy_left_side_sim", icon='MESH_CUBE', text="Copy Left Side to Right Side Sim")
                layout.operator("s4animtools.copy_baked_animation", icon='MESH_CUBE', text="Copy Baked Animation")
                # self.layout.operator("s4animtools.copy_left_side_sim_selected", icon='MESH_CUBE', text="Copy Left Side (Sim) Selected")
                layout.operator("s4animtools.maintain_keyframe", icon="MESH_CUBE",
                                     text="Maintain Keyframe").direction = "FORWARDS"
                layout.operator("s4animtools.maintain_keyframe", icon="MESH_CUBE",
                                     text="Maintain Keyframe Backward").direction = "BACK"

                layout = self.layout
                layout.operator("s4animtools.import_rig", icon='MESH_CUBE', text="Import Rig")

                layout.operator("s4animtools.export_rig", icon='MESH_CUBE', text="Export Rig")


            layout.prop(obj, "show_ik_options", text="Show IK Options")
            if obj.show_ik_options:
                layout.operator("s4animtools.create_finger_ik", icon='MESH_CUBE', text="Create Finger IK")
                layout.operator("s4animtools.create_ik_rig", icon='MESH_CUBE', text="Create IK Rig")
                self.layout.operator('iktarget.create_roots', text='Create World IK Channels')

                layout = self.layout
                box = layout.row()
                row = box

                if obj.ik_idx >= 0 and obj.ik_targets:
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
                row.operator('iktarget.new', text='New').command = ""
                layout = self.layout.row()

                layout.operator("s4animtools.bakeik", text="Set IK Weight")
                layout.operator("s4animtools.muteik", text="Mute IK")
                layout.operator("s4animtools.unmuteik", text="Unmute IK")

                layout.operator("s4animtools.removeik", text="Remove IK")

                layout.operator("s4animtools.preview_ik", text="Preview IK")
                layout.operator("s4animtools.update_ik_empties", text="Update IK Empties")
                layout.scale_x = 1

                layout = self.layout.row()
                try:
                    if context.object.pose.bones["b__L_Hand__"].constraints["Copy Rotation"].enabled:
                        layout.operator("s4animtools.ik_to_fk", icon='MESH_CUBE',
                                        text="IK To FK (L Arm)").command = "LEFT,HAND"
                    else:
                        layout.operator("s4animtools.fk_to_ik", icon='MESH_CUBE',
                                        text="FK To IK (L Arm)").command = "LEFT,HAND"
                    if context.object.pose.bones["b__R_Hand__"].constraints["Copy Rotation"].enabled:
                        layout.operator("s4animtools.ik_to_fk", icon='MESH_CUBE',
                                        text="IK To FK (R Arm)").command = "RIGHT,HAND"
                    else:
                        layout.operator("s4animtools.fk_to_ik", icon='MESH_CUBE',
                                        text="FK To IK (R Arm)").command = "RIGHT,HAND"

                    if context.object.pose.bones["b__L_Foot__"].constraints["Copy Rotation"].enabled:
                        layout.operator("s4animtools.ik_to_fk", icon='MESH_CUBE',
                                        text="IK To FK (L Leg)").command = "LEFT,FOOT"
                    else:
                        layout.operator("s4animtools.fk_to_ik", icon='MESH_CUBE',
                                        text="FK To IK (L Leg)").command = "LEFT,FOOT"
                    if context.object.pose.bones["b__R_Foot__"].constraints["Copy Rotation"].enabled:
                        layout.operator("s4animtools.ik_to_fk", icon='MESH_CUBE',
                                        text="IK To FK (R Leg)").command = "RIGHT,FOOT"
                    else:
                        layout.operator("s4animtools.fk_to_ik", icon='MESH_CUBE',
                                        text="FK To IK (R Leg)").command = "RIGHT,FOOT"
                    #         layout.prop(obj, "select_slots", text = "Slots")
                except KeyError:
                    pass

            layout.prop(obj, "show_initial_offset_options", text="Show Initial Offset Options")
            if obj.show_initial_offset_options:
                layout = self.layout.row()

                layout.prop_search(context.object, "relative_rig", context.scene, "objects", text="Initial Offsets Rig")
                if len(context.object.relative_rig) > 0:
                    if context.object.relative_rig in bpy.data.objects:
                        relative_rig_obj = bpy.data.objects[context.object.relative_rig]
                        layout.prop_search(context.object, "relative_bone", relative_rig_obj.pose, "bones",
                                           text="Initial Offsets Bone")
                layout = self.layout.row()
                layout.scale_x = 0.4
                layout.label(text="Initial Offset Q")
                layout.scale_x = 0.5

                layout.prop(obj, "initial_offset_q", text="")
                layout.scale_x = 0.4
                layout.label(text="Initial Offset T")

                layout.prop(obj, "initial_offset_t", text="")

            self.layout.prop(obj, "show_events", text="Show Events")
            if obj.show_events:
                self.layout.operator("s4animtools.initialize_events", text="Initialize Events")
                self.draw_events(obj, "parent_events_list", 0.1,
                                 "Parameters (Frame/Object To Be Parented/Object To Be Parented To/Bone)",
                                 "Parent Events", self.layout,
                                 parameters=["Frame", "Object to Be Parented", "Object to be Parented To", "Bone"])

                self.draw_events(obj, "sound_events_list", 0.1, "Parameters (Frame Number/Sound Effect Name)",
                                 "Sound Events", self.layout, parameters=["Frame", "Sound Effect Name"])
                self.draw_events(obj, "script_events_list", 0.1, "Parameters (Frame Number/Script Xevt)",
                                 "Script Events",
                                 self.layout, parameters=["Frame", "Script Xevt"])
                self.draw_events(obj, "snap_events_list", 0.1, "Parameters (Frame Number/Actor/Translation/Quaternion)",
                                 "Snap Events", self.layout,
                                 parameters=["Frame", "Actor", "X", "Y", "Z", "QX", "QY", "QZ", "QW", ])
                self.draw_events(obj, "reaction_events_list", 0.1,
                                 "Parameters (Frame Number/Reaction ASM/Reaction State)",
                                 "Reaction Events", self.layout,
                                 parameters=["Frame", "Reaction ASM Name", "Reaction State Name"])
                self.draw_events(obj, "play_effect_events_list", 0.1,
                                 "Parameters (Frame Number/VFX Name/Actor Name/Bone Name/(always 0)/(almost always 0)/Unique VFX Name)",
                                 "Play Effect Events", self.layout,
                                 parameters=["Frame", "VFX Name", "Actor Name", "Bone Name", "(always 0)",
                                             "(almost always 0)", "Unique VFX Name"])
                self.draw_events(obj, "stop_effect_events_list", 0.1,
                                 "Parameters (Frame Number/Unique VFX Name/(always 0)/Unknown Bool 1)",
                                 "Stop Effect Events", self.layout,
                                 parameters=["Frame", "Unique VFX Name", "(always 0)", "(unknown bool)"])
                self.draw_events(obj, "disable_lipsync_events_list", 0.1, "Parameters (Frame Number/Duration)",
                                 "Suppress Lipsync Events", self.layout, parameters=["Frame", "End Frame"])
                self.draw_events(obj, "visibility_events_list", 0.1, "Parameters (Frame Number/Actor/Visibility)",
                                 "Visibility Events", self.layout,
                                 parameters=["Frame", "Actor Name", "Visibility (0 or 1)"])
                self.draw_events(obj, "focus_compatibility_events_list", 0.1, "Parameters (End Frame,Level)",
                                 "Focus Compatibility Events", self.layout)
            self.layout.prop(obj, "show_experimental_options", text="Show Experimental Options")
            if obj.show_experimental_options:
                self.layout.label(text="Use Full Precision means using full precision for all animation data.")
                self.layout.label(text="Don't enable if you don't know what that means! ")
                self.layout.label(text="This will cause unnecessarily large file sizes and has a hard limit on how much animation data can be stored.")
                self.layout.prop(obj, "use_full_precision", text="EXPERIMENTAL!! Use Full Precision")
                self.layout.prop(obj, "use_world_bone_as_root",
                                text="Use World Rig and Bone as Root for IK Targets on Object")
                self.layout.label(text="The base rig is only used for additive animations such as the infant carrier from Growing Together.")
                self.layout.label(text="The base rig setting is not used for normal animations.")
                self.layout.prop_search(obj, "base_rig", context.scene, "objects", text="Base Rig")
                self.layout.label(text="Export an Additive Clip. Do not use for normal animations")
                self.layout.operator("s4animtools.new_export_clip", icon='MESH_CUBE', text="Export Additive Clip").additive = True

        if obj is not None:
            layout = self.layout
            layout = self.layout.row()



            try:
                selected_bone = bpy.context.selected_pose_bones[0]

                self.layout.label(text=selected_bone.name)
                for ik_idx in range(-1,11):
                    row = self.layout.row()
                    row.scale_x = 1
                    if ik_idx == -1:
                        row.prop(selected_bone, f"ik_pos_{ik_idx}", text=f"Pos")
                        row.prop(selected_bone, f"ik_rot_{ik_idx}", text=f"Rot")

                    else:
                        row.prop(selected_bone, f"ik_pos_{ik_idx}", text=f"IK Pos {ik_idx}")
                        row.prop(selected_bone, f"ik_rot_{ik_idx}", text=f"IK Rot {ik_idx}")
                    row.scale_x = 2.5
                    row.prop(selected_bone, f"ik_weight_{ik_idx}", text=f"IK Weight {ik_idx}")

            except Exception as e:
                pass



            if obj.is_enabled_for_animation:
                self.layout.prop(context.scene, "s4animtools_export_path", text="Export Path")

                self.layout.prop(obj, "allow_jaw_animation_for_entire_animation",
                                 text="Allow Jaw Animation For Entire Animation (Use this for poses or posepacks)")

                self.layout.operator("s4animtools.new_export_clip", icon='MESH_CUBE', text="Export Clip")

                # self.layout.prop(context.scene, "IK_bone_target")  # String for displaying current IK bone\
                self.layout.prop(context.scene, "clip_splits", text="Clip Split Point(s)")

               # self.layout.label(text="Clip Split Points are the points in the animation where the clip will be split.")
               # self.layout.label(text="This is useful for animations that have multiple parts.")
               # self.layout.label(text="For example, a dance animation that has a start, loop, and end.")
               # self.layout.label(text="You can specify multiple clip split points with commas.")
               # self.layout.label(text="Example: 30,75,110")
               # self.layout.label(text="If you only have one clip, enter it without a comma.")
                self.layout.prop(context.scene, "clip_name_prefix", text = "Clip Name Prefix(es)")  # clip_name_prefix
              #  self.layout.label(text="The clip name prefix is the prefix that will be added to the clip name.")
              #  self.layout.label(text="If your clip names all start with a2o_dance, for example.")
              #  self.layout.label(text="You can specify a clip name prefix of a2o_dance.")
              #  self.layout.label(text="If you don't want to use a clip name prefix, leave this blank.")


                self.layout.prop(context.scene, "clip_name", text = "Clip Name(s)")
             #   self.layout.label(text="If you have more than one clip in this blend file.")
             #   self.layout.label(text="you can specify multiple clip names with commas.")
             #   self.layout.label(text="Example: a2o_dance_start,a2o_dance_loop,a2o_dance_end")
             #   self.layout.label(text="If you only have one clip name, enter it without a comma.")
                self.layout.prop(obj, "is_overlay", text="Is Overlay")

                self.layout.prop(obj, "disable_rig_suffix", text ="Disable Rig Suffix")
              #  self.layout.label(text="Disable the rig suffix. For example:")
              #  self.layout.label(text="a2o_dance_start would become a2o_dance_start_x")
              #  self.layout.label(text="if you were exporting a clip for the x rig.")

                self.layout.prop(obj, "reset_initial_offset_t", text="Reset Initial Offset T")

              #  layout.label(text="The world rig is where the root of your exported animation will be located.")
               # layout.label(text="This is handy if you accidentally animated your sim in the wrong spot and don't want to remake it.")
                self.layout.prop_search(context.object, "world_rig", context.scene, "objects", text="World Rig")
                if len(context.object.world_rig) > 0:
                    if context.object.world_rig in bpy.data.objects:
                        target_bone_obj = bpy.data.objects[obj.world_rig]
                        self.layout.prop_search(context.object, "world_bone", target_bone_obj.pose, "bones", text="World Bone")


                self.layout.prop(obj, "explicit_namespaces", text="Explicit Namespaces")
                self.layout.prop(obj, "reference_namespace_hash", text="Reference Namespace Hash")


                self.layout.prop(obj, "additional_snap_frames", text="Additional Snap Frames")
                self.layout.prop(obj, "rig_name", text="Rig Name")  # String for current clip actor
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
                    box = self.draw_ik_target(context, current_chain_idx, item, obj, box, ik_chain_count)
                    current_chain_idx += 1

            elif item.chain_bone == chain_bone:

                box = self.draw_ik_target(context, current_chain_idx, item, obj, box, ik_chain_count)
                current_chain_idx += 1
        return row

    def draw_ik_target(self, context, idx, item, obj, row, ik_chain_count):
        sub = row.row()
        #sub = row.row()
        actual_idx = -1
        for new_idx, ik_target in enumerate(obj.ik_targets):
            if ik_target == item:
                actual_idx = new_idx
        sub.label(text="IK Target")
        sub.scale_x = 1

        sub.prop(item, "chain_idx", text="Chain")

        sub.scale_x = 0.5
        sub.operator('iktarget.delete_specific', text='Delete').command = str(actual_idx)
        #print(idx, ik_chain_count, item.chain_bone)
        if idx == ik_chain_count - 1:
            sub.operator('iktarget.new', text='Clone').command = f"{item.chain_bone}"

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


class TimeRange(PropertyGroup):
    start_time: IntProperty(name="Start", description="IK Start",
                            default=0, min=0, soft_max=360)
    end_time: IntProperty(name="End", description="IK End",
                          default=0, min=0, soft_max=360)


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
    actor_enabled: bpy.props.BoolProperty(default=True)
    initial_offset_quaternion: bpy.props.PointerProperty(type=QuaternionConfig)
    initial_offset_position: bpy.props.PointerProperty(type=PositionConfig)


class S4ANIMTOOLS_OT_move_new_element(bpy.types.Operator):
    bl_idname = "s4animtools.move_new_element"
    bl_label = ""
    bl_options = {"REGISTER", "UNDO"}

    args: bpy.props.StringProperty()

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


class IKTarget(PropertyGroup):
    chain_bone: bpy.props.StringProperty()
    holder_src_bone: bpy.props.StringProperty()

    target_obj: bpy.props.StringProperty()
    target_bone: bpy.props.StringProperty()
    chain_idx: IntProperty(name="Chain Idx", description="Chain index of the ik chain.",
                           default=-1, min=-1, max=9)
    start_time: IntProperty(name="Start", description="Start Time",
                            default=0, min=0, soft_max=360, options={'HIDDEN'})
    end_time: IntProperty(name="End", description="End Time",
                          default=0, min=0, soft_max=360, options={'HIDDEN'})
    ranges: CollectionProperty(type=TimeRange)


class AnimationEvent(PropertyGroup):
    info: bpy.props.StringProperty()


class ClipData(PropertyGroup):
    clip_name: bpy.props.StringProperty()
    clip_uses_prefix: bpy.props.BoolProperty()
    actor_1: bpy.props.StringProperty()
    actor_2: bpy.props.StringProperty()
    actor_3: bpy.props.StringProperty()

    ranges: CollectionProperty(type=TimeRange)


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
        human_bones = _s4animtools.bone_names.human_bones
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
        return {"FINISHED"}


def update_initial_offsets(self, context):
    active_object_root = context.active_object.pose.bones["b__ROOT__"]
    if context.object.relative_rig == "":
        relative_rig = context.active_object
        relative_bone = None
    else:
        relative_rig = bpy.data.objects[context.object.relative_rig]
        relative_bone = relative_rig.pose.bones[context.object.relative_bone]
    object_matrix = relative_rig.matrix_world @ relative_bone.matrix
    x_matrix = context.active_object.matrix_world @ active_object_root.matrix
    offset = object_matrix.inverted() @ x_matrix

    rotation = offset.to_quaternion()
    translation = offset.to_translation()

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

        anim_path = os.path.join(os.environ["HOMEPATH"], "Desktop", "Animation Workspace",
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

def is_slot_bone(bone):
    return "slot" in bone.name.lower()

def is_cas_bone(bone):
    return "cas" in bone.name.lower()

def is_left_bone(bone):
    return "_l_" in bone.name.lower()

def is_right_bone(bone):
    return "_r_" in bone.name.lower()

def is_middle_bone(bone):
    if is_left_bone(bone):
        return False
    if is_right_bone(bone):
        return False
    return True
def is_mouth(bone):
    if bone.parent is None:
        return False
    if bone.parent.name == "b__CAS_LowerMouthArea__":
        return True
    if bone.parent.name == "b__CAS_UpperMouthArea__":
        return True
    return False
def check_if_finger_bone(bone):
    if bone.parent is not None:
        if "hand" in bone.parent.name.lower():
            return True
        if bone.parent.parent is not None:
            if "hand" in bone.parent.parent.name.lower():
                return True

            if bone.parent.parent.parent is not None:

                if "hand" in bone.parent.parent.parent.name.lower():
                    print(bone.name)
                    return True
    return False

def is_left_pinky_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "pinky" in bone.name.lower() and is_left_bone(bone)

def is_left_ring_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "ring" in bone.name.lower() and is_left_bone(bone)

def is_left_mid_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "mid" in bone.name.lower() and is_left_bone(bone)

def is_left_index_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "index" in bone.name.lower() and is_left_bone(bone)

def is_left_thumb_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "thumb" in bone.name.lower() and is_left_bone(bone)

def is_slot_bone(bone):
    return "slot" in bone.name

def is_first_left_finger_joint(bone):
    if is_left_pinky_bone(bone) or is_left_ring_bone(bone) or is_left_mid_bone(bone) or is_left_index_bone(
            bone) or is_left_thumb_bone(bone):
        if "0" in bone.name:
            return True

    return False

def is_second_left_finger_joint(bone):
    if is_left_pinky_bone(bone) or is_left_ring_bone(bone) or is_left_mid_bone(bone) or is_left_index_bone(
            bone) or is_left_thumb_bone(bone):
        if "1" in bone.name:
            return True

    return False

def is_third_left_finger_joint(bone):
    if is_left_pinky_bone(bone) or is_left_ring_bone(bone) or is_left_mid_bone(bone) or is_left_index_bone(
            bone) or is_left_thumb_bone(bone):
        if "2" in bone.name:
            return True

    return False

def is_left_finger_joint(bone):
    if is_left_pinky_bone(bone) or is_left_ring_bone(bone) or is_left_mid_bone(bone) or is_left_index_bone(
            bone) or is_left_thumb_bone(bone):
        return True

    return False

def is_right_pinky_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "pinky" in bone.name.lower() and is_right_bone(bone)

def is_right_ring_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "ring" in bone.name.lower() and is_right_bone(bone)

def is_right_mid_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "mid" in bone.name.lower() and is_right_bone(bone)

def is_right_index_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "index" in bone.name.lower() and is_right_bone(bone)

def is_right_thumb_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "thumb" in bone.name.lower() and is_right_bone(bone)


def is_first_right_finger_joint(bone):
    if is_right_pinky_bone(bone) or is_right_ring_bone(bone) or is_right_mid_bone(bone) or is_right_index_bone(
            bone) or is_right_thumb_bone(bone):
        if "0" in bone.name:
            return True

    return False

def is_second_right_finger_joint(bone):
    if is_right_pinky_bone(bone) or is_right_ring_bone(bone) or is_right_mid_bone(bone) or is_right_index_bone(
            bone) or is_right_thumb_bone(bone):
        if "1" in bone.name:
            return True

    return False

def is_third_right_finger_joint(bone):
    if is_right_pinky_bone(bone) or is_right_ring_bone(bone) or is_right_mid_bone(bone) or is_right_index_bone(
            bone) or is_right_thumb_bone(bone):
        if "2" in bone.name:
            return True

    return False

def is_right_finger_joint(bone):
    if is_right_pinky_bone(bone) or is_right_ring_bone(bone) or is_right_mid_bone(bone) or is_right_index_bone(
            bone) or is_right_thumb_bone(bone):
        return True

    return False


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

class OT_S4ANIMTOOLS_FKToIK(bpy.types.Operator):
    bl_idname = "s4animtools.fk_to_ik"
    bl_label = "FK To IK"
    bl_options = {"REGISTER", "UNDO"}
    command: bpy.props.StringProperty()

    def execute(self, context):
        from mathutils import Matrix
        # TODO reset forearm and calf bones location and rotation when switching modes
        # What gets activated
        # Left Hand Target
        # Left Hand IK
        # Left Arm Pole
        # Left Hand IK Constraint to Left Hand Target
        # What gets hidden
        # Left Upper Arm
        # Left Forearm
        # Left Hand
        arm = context.object.data
        pose = context.object.pose

        if "LEFT,HAND" == self.command:
            hand = "b__L_Hand__"
            forearm = "b__L_Forearm__"
            upper_arm = "b__L_UpperArm__"
            target = "Left Hand Target"
            pole = "Left Arm Pole"
            export_pole = "b__L_ArmExportPole__"
            ik = "Left Hand IK"

        elif "RIGHT,HAND" == self.command:
            hand = "b__R_Hand__"
            forearm = "b__R_Forearm__"
            upper_arm = "b__R_UpperArm__"
            target = "Right Hand Target"
            pole = "Right Arm Pole"
            export_pole = "b__R_ArmExportPole__"
            ik = "Right Hand IK"

        elif "LEFT,FOOT" == self.command:
            hand = "b__L_Foot__"
            forearm = "b__L_Calf__"
            upper_arm = "b__L_Thigh__"
            target = "Left Foot Main Parent"
            pole = "Left Leg Pole"
            export_pole = "b__L_LegExportPole__"
            ik = "Left Foot IK"

        elif "RIGHT,FOOT" == self.command:
            hand = "b__R_Foot__"
            forearm = "b__R_Calf__"
            upper_arm = "b__R_Thigh__"
            target = "Right Foot Main Parent"
            pole = "Right Leg Pole"
            export_pole = "b__R_LegExportPole__"
            ik = "Right Foot IK"
        else:
            return {"FINISHED"}
        if ik in pose.bones:
            left_hand_ik = pose.bones[ik]
            left_arm_pole = pose.bones[export_pole]
            matrix_data = pose.bones[pole].matrix.copy()

            left_arm_pole.matrix = matrix_data
            left_arm_pole.keyframe_insert(data_path="location", frame=context.scene.frame_current)

            left_hand = pose.bones[target]



            matrix_data = pose.bones[hand].matrix.copy()
            pose.bones[hand].constraints["Copy Rotation"].enabled = True
            context.object.keyframe_insert(data_path=r'pose.bones["{}"].constraints["Copy Rotation"].enabled'.format(hand), frame=context.scene.frame_current)

            left_hand.matrix = matrix_data
            left_hand.keyframe_insert(data_path="location", frame=context.scene.frame_current)
            left_hand.keyframe_insert(data_path="rotation_quaternion", frame=context.scene.frame_current)
            left_hand.keyframe_insert(data_path="rotation_euler", frame=context.scene.frame_current)

            pose.bones[forearm].matrix_basis = Matrix()
            pose.bones[forearm].keyframe_insert(data_path="location", frame=context.scene.frame_current)
            pose.bones[forearm].keyframe_insert(data_path="rotation_euler", frame=context.scene.frame_current)
            pose.bones[forearm].keyframe_insert(data_path="rotation_quaternion", frame=context.scene.frame_current)

            # Enable the left hand ik constraint
            left_hand_ik.constraints["IK"].enabled = True
            context.object.keyframe_insert(data_path=r'pose.bones["{}"].constraints["IK"].enabled'.format(ik), frame=context.scene.frame_current)

            # Setup bone visibility
            pose.bones[target].bone.hide = False
            pose.bones[ik].bone.hide = True
            pose.bones[export_pole].bone.hide = False
            pose.bones[pole].bone.hide = True

            pose.bones[upper_arm].bone.hide = True
            pose.bones[forearm].bone.hide = True
            pose.bones[hand].bone.hide = True

            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(target), frame=context.scene.frame_current)
            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(ik), frame=context.scene.frame_current)
            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(export_pole), frame=context.scene.frame_current)
            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(pole), frame=context.scene.frame_current)
            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(upper_arm), frame=context.scene.frame_current)
            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(forearm), frame=context.scene.frame_current)
            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(hand), frame=context.scene.frame_current)



        return {"FINISHED"}
class OT_S4ANIMTOOLS_IKToFK(bpy.types.Operator):
    bl_idname = "s4animtools.ik_to_fk"
    bl_label = "IK To FK"
    bl_options = {"REGISTER", "UNDO"}
    command: bpy.props.StringProperty()

    def execute(self, context):
        arm = context.object.data
        pose = context.object.pose

        if "LEFT,HAND" == self.command:
            hand = "b__L_Hand__"
            forearm = "b__L_Forearm__"
            upper_arm = "b__L_UpperArm__"
            target = "Left Hand Target"
            pole = "Left Arm Pole"
            export_pole = "b__L_ArmExportPole__"
            ik = "Left Hand IK"

        elif "RIGHT,HAND" == self.command:
            hand = "b__R_Hand__"
            forearm = "b__R_Forearm__"
            upper_arm = "b__R_UpperArm__"
            target = "Right Hand Target"
            pole = "Right Arm Pole"
            export_pole = "b__R_ArmExportPole__"
            ik = "Right Hand IK"
        elif "LEFT,FOOT" == self.command:
            hand = "b__L_Foot__"
            forearm = "b__L_Calf__"
            upper_arm = "b__L_Thigh__"
            target = "Left Foot Main Parent"
            pole = "Left Leg Pole"
            export_pole = "b__L_LegExportPole__"
            ik = "Left Foot IK"

        elif "RIGHT,FOOT" == self.command:
            hand = "b__R_Foot__"
            forearm = "b__R_Calf__"
            upper_arm = "b__R_Thigh__"
            target = "Right Foot Main Parent"
            pole = "Right Leg Pole"
            export_pole = "b__R_LegExportPole__"
            ik = "Right Foot IK"
        else:
            return {"FINISHED"}

        if ik in pose.bones:
            left_hand_ik = pose.bones[ik]
            left_upper_arm = pose.bones[upper_arm]
            matrix_data = left_upper_arm.matrix.copy()

            left_upper_arm.matrix = matrix_data
            left_upper_arm.keyframe_insert(data_path="location", frame=context.scene.frame_current)
            left_upper_arm.keyframe_insert(data_path="rotation_quaternion", frame=context.scene.frame_current)
            left_upper_arm.keyframe_insert(data_path="rotation_euler", frame=context.scene.frame_current)
            left_forearm = pose.bones[forearm]
            matrix_data = left_forearm.matrix.copy()

            left_forearm.matrix = matrix_data
            left_forearm.keyframe_insert(data_path="location", frame=context.scene.frame_current)
            left_forearm.keyframe_insert(data_path="rotation_quaternion", frame=context.scene.frame_current)
            left_forearm.keyframe_insert(data_path="rotation_euler", frame=context.scene.frame_current)

            left_hand = pose.bones[hand]
            matrix_data = left_hand.matrix.copy()
            left_hand.constraints["Copy Rotation"].enabled = False
            context.object.keyframe_insert(data_path=r'pose.bones["{}"].constraints["Copy Rotation"].enabled'.format(hand), frame=context.scene.frame_current)

            left_hand.matrix = matrix_data
            left_hand.keyframe_insert(data_path="location", frame=context.scene.frame_current)
            left_hand.keyframe_insert(data_path="rotation_quaternion", frame=context.scene.frame_current)
            left_hand.keyframe_insert(data_path="rotation_euler", frame=context.scene.frame_current)
            left_hand_ik.constraints["IK"].enabled = False
            context.object.keyframe_insert(data_path=r'pose.bones["{}"].constraints["IK"].enabled'.format(ik), frame=context.scene.frame_current)

            pose.bones[target].bone.hide = True
            pose.bones[ik].bone.hide = True
            pose.bones[export_pole].bone.hide = True
            pose.bones[pole].bone.hide = True

            pose.bones[upper_arm].bone.hide = False
            pose.bones[forearm].bone.hide = False
            pose.bones[hand].bone.hide = False

            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(target), frame=context.scene.frame_current)
            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(ik), frame=context.scene.frame_current)
            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(export_pole), frame=context.scene.frame_current)
            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(pole), frame=context.scene.frame_current)
            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(upper_arm), frame=context.scene.frame_current)
            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(forearm), frame=context.scene.frame_current)
            context.object.data.keyframe_insert(data_path=r'bones["{}"].hide'.format(hand), frame=context.scene.frame_current)



        return {"FINISHED"}

class OT_S4ANIMTOOLS_MaskOutParents(bpy.types.Operator):
    bl_idname = "s4animtools.mask_out_parents"
    bl_label = "Mask Out Parents"
    bl_options = {"REGISTER", "UNDO"}
    command: bpy.props.StringProperty()


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
    command: bpy.props.StringProperty()


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

class OT_S4ANIMTOOLS_PreviewIK(bpy.types.Operator):
    bl_idname = "s4animtools.preview_ik"
    bl_label = "Preview IK"
    bl_options = {"REGISTER", "UNDO"}


    def cleanup_stale_empties(self):
        for obj in bpy.data.objects:
            if obj.name.startswith("IKEmpty_"):
                bpy.data.objects.remove(obj)

    def execute(self, context):
        obj = context.object
        # Note: this assumes there is only one possible actor to go into Slot selection mode at a time
        self.cleanup_stale_empties()
        ik_target_per_bone = defaultdict(int)
        for idx, target in enumerate(get_ik_targets(obj)):
            bone_id = hex(get_32bit_hash(
                "{}_{}_{}_{}".format(obj.rig_name, target.chain_bone, target.target_obj, target.target_bone).encode(
                    "utf-8")))
            hashed_id = "IKEmpty_{}_UserAdjust".format(bone_id)
            o = bpy.data.objects.new(hashed_id, None)
            o.rotation_mode = 'QUATERNION'
            bpy.context.scene.collection.objects.link(o)
            o.empty_display_size = 0.01
            o.empty_display_type = 'PLAIN_AXES'
            # Create a child of constraint on the new empty.
            c = o.constraints.new('CHILD_OF')
            c.target = bpy.data.objects[target.target_obj]
            c.subtarget = target.target_bone
            bpy.context.view_layer.objects.active = o
            o.select_set(True)
            context_py = bpy.context.copy()
            context_py["constraint"] = c
            bpy.ops.constraint.childof_clear_inverse(context_py, constraint="Child Of", owner='OBJECT')


            # Create animated slot offset driven by drivers
            # This needs to be separated from UserAdjust so the user can adjust the slot offset
            # and then the driver applies it relative to the UserAdjust
            hashed_id = "IKEmpty_{}_DriverAdjust".format(bone_id)
            o2 = bpy.data.objects.new(hashed_id, None)
            o2.rotation_mode = 'QUATERNION'
            bpy.context.scene.collection.objects.link(o2)
            o2.empty_display_size = 0.1
            o2.empty_display_type = 'PLAIN_AXES'
            o2.parent = o
            bpy.context.view_layer.objects.active = o2
            o2.select_set(True)


            for j in range(3):
                location = o2.driver_add("location", j)
                v = location.driver.variables.new()
                driver_target = v.targets[0]
                driver_target.id = obj
                driver_target.data_path = 'pose.bones["{}"].ik_pos_{}[{}]'.format(target.chain_bone, ik_target_per_bone[target.chain_bone], j)
                location.driver.expression = v.name

            for k in range(4):
                location = o2.driver_add("rotation_quaternion", k)
                v = location.driver.variables.new()
                driver_target = v.targets[0]
                driver_target.id = obj
                driver_target.data_path = 'pose.bones["{}"].ik_rot_{}[{}]'.format(target.chain_bone, ik_target_per_bone[target.chain_bone], k)
                location.driver.expression = v.name
            ik_target_per_bone[target.chain_bone] += 1
        return {"FINISHED"}


class OT_S4ANIMTOOLS_UpdateIKEmpties(bpy.types.Operator):
    bl_idname = "s4animtools.update_ik_empties"
    bl_label = "Update IK Empties"
    bl_options = {"REGISTER", "UNDO"}

    LEFT_HAND = "b__L_Hand__"
    RIGHT_HAND = "b__R_Hand__"
    LEFT_FOOT = "b__L_Foot__"
    RIGHT_FOOT = "b__R_Foot__"

    ik_bones = [LEFT_HAND, RIGHT_HAND, LEFT_FOOT, RIGHT_FOOT]


    def get_matching_bone_name(self, target):
        target_bone = None

        if target == "b__L_Hand__":
            target_bone = "Left Hand Target"
        elif target == "b__R_Hand__":
            target_bone = "Right Hand Target"
        elif target == "b__L_Foot__":
            target_bone = "Left Foot Target"
        elif target == "b__R_Foot__":
            target_bone = "Right Foot Target"
        return target_bone
    def cleanup_stale_constraints(self, context):
        # NOTE! This assumes your IK bones are the target bones. Not the bone where the ik constraint lives on.
        for bone_name in self.ik_bones:
            target_bone = self.get_matching_bone_name(bone_name)
            if target_bone in context.object.pose.bones:
                for constraint in context.object.pose.bones[target_bone].constraints[:]:
                    print(constraint)
                    if constraint.type == 'COPY_TRANSFORMS':
                        context.object.pose.bones[target_bone].constraints.remove(constraint)


    def execute(self, context):
        obj = context.object
        # Note: this assumes there is only one possible actor to go into Slot selection mode at a time
        self.cleanup_stale_constraints(context)
        ik_target_per_bone = defaultdict(int)
        for idx, target in enumerate(get_ik_targets(obj)):
            bone_id = hex(get_32bit_hash(
                "{}_{}_{}_{}".format(obj.rig_name, target.chain_bone, target.target_obj, target.target_bone).encode(
                    "utf-8")))
            driver_adjust_obj = "IKEmpty_{}_DriverAdjust".format(bone_id)
            if "b__ROOT_bind__" == target.chain_bone:
                continue
            target_bone = self.get_matching_bone_name(target.chain_bone)
            if target_bone is None:
                continue
            c = obj.pose.bones[target_bone].constraints.new('COPY_TRANSFORMS')
            c.target = bpy.data.objects[driver_adjust_obj]
            if ik_target_per_bone[target.chain_bone] >= 1:
                location = c.driver_add("influence")
                for v in location.driver.variables[:]:
                    location.driver.variables.remove(v)
                v = location.driver.variables.new()
                driver_target = v.targets[0]
                driver_target.id = obj
                driver_target.data_path = 'pose.bones["{}"].ik_weight_{}'.format(target.chain_bone, ik_target_per_bone[target.chain_bone])
                location.driver.expression = v.name
            ik_target_per_bone[target.chain_bone] += 1

        return {"FINISHED"}

classes = (
    Snapper, ExportRig, SyncRigToMesh,
    S4ANIMTOOLS_PT_MainPanel,
    TimeRange,
    IKTarget, s4animtool_PT_IKTargetPanel, LIST_OT_NewIKTarget, LIST_OT_CreateIKTarget, LIST_OT_DeleteIKTarget, LIST_OT_MoveIKTarget,
    s4animtool_OT_bakeik, s4animtool_OT_removeIK,s4animtools_OT_guessTarget,
    BeginIKMarker, s4animtool_OT_unmute_ik, s4animtool_OT_mute_ik, NewClipExporter, PositionConfig, QuaternionConfig,
    ActorSettings, ClipData, ImportRig, CopyLeftSideAnimationToRightSide, CopyLeftSideAnimationToRightSideSim, CopyBakedAnimationToControlRig,
    CopySelectedLeftSideToRightSide, ExportAnimationStateMachine, MaintainKeyframe, AnimationEvent, InitializeEvents,
    S4ANIMTOOLS_OT_move_new_element, AnimationEvent,
    LIST_OT_NewIKRange, LIST_OT_DeleteIKRange, LIST_OT_DeleteSpecificIKTarget, FlipLeftSideAnimationToRightSideSim, OT_S4ANIMTOOLS_ImportFootprint,OT_S4ANIMTOOLS_ExportFootprint,
    OT_S4ANIMTOOLS_VisualizeFootprint, OT_S4ANIMTOOLS_CreateBoneSelectors, OT_S4ANIMTOOLS_CreateFingerIK, OT_S4ANIMTOOLS_CreateIKRig,
    OT_S4ANIMTOOLS_FKToIK, OT_S4ANIMTOOLS_IKToFK, OT_S4ANIMTOOLS_DetermineBalance, OT_S4ANIMTOOLS_MaskOutParents, OT_S4ANIMTOOLS_ApplyTrackmask, OT_S4ANIMTOOLS_MaskOutChildren,
OT_S4ANIMTOOLS_PreviewIK, OT_S4ANIMTOOLS_UpdateIKEmpties, S4ANIMTOOL_OT_ExportAllClips)

def update_selected_bones(self, context):
    pass

def register():
    """Register classes for the things."""
    from bpy.utils import register_class
    for cls in classes:
        try:
            register_class(cls)
        except Exception as e:
            print(e)
    bpy.types.PoseBone.mirrored_bone = bpy.props.StringProperty()
    bpy.types.PoseBone.bone_flags = bpy.props.StringProperty()

    # This is for the baked IK data
    for ik_idx in range(-1,11):
        setattr(bpy.types.PoseBone, f"ik_pos_{ik_idx}", bpy.props.FloatVectorProperty(size=3))
        setattr(bpy.types.PoseBone, f"ik_rot_{ik_idx}", bpy.props.FloatVectorProperty(default=(0,0,0,1), size=4, min=-1, max=1))
        setattr(bpy.types.PoseBone, f"ik_weight_{ik_idx}", bpy.props.FloatProperty(min=0, max=1))

    bpy.types.Object.is_footprint = bpy.props.BoolProperty(default=False)

    bpy.types.Object.for_placement = bpy.props.BoolProperty(default=False)
    bpy.types.Object.for_pathing = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_enabled = bpy.props.BoolProperty(default=False)
    bpy.types.Object.discouraged = bpy.props.BoolProperty(default=False)
    bpy.types.Object.landing_strip = bpy.props.BoolProperty(default=False)
    bpy.types.Object.no_raycast = bpy.props.BoolProperty(default=False)
    bpy.types.Object.placement_slotted = bpy.props.BoolProperty(default=False)
    bpy.types.Object.encouraged = bpy.props.BoolProperty(default=False)
    bpy.types.Object.terrain_cutout = bpy.props.BoolProperty(default=False)




    bpy.types.Object.slope = bpy.props.BoolProperty(default=False)
    bpy.types.Object.outside = bpy.props.BoolProperty(default=False)
    bpy.types.Object.inside = bpy.props.BoolProperty(default=False)

    bpy.types.Object.terrain = bpy.props.BoolProperty(default=False)
    bpy.types.Object.floor = bpy.props.BoolProperty(default=False)
    bpy.types.Object.pool = bpy.props.BoolProperty(default=False)
    bpy.types.Object.pond = bpy.props.BoolProperty(default=False)
    bpy.types.Object.fence_post = bpy.props.BoolProperty(default=False)
    bpy.types.Object.any_surface = bpy.props.BoolProperty(default=False)
    bpy.types.Object.air = bpy.props.BoolProperty(default=False)
    bpy.types.Object.roof = bpy.props.BoolProperty(default=False)

    bpy.types.Object.is_none = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_walls = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_objects = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_sims = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_roofs = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_fences = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_modular_stairs = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_objects_of_same_type = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_columns = bpy.props.BoolProperty(default=False)

    bpy.types.Object.is_reserved_space = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_foundations = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_fenestration_node = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_trim = bpy.props.BoolProperty(default=False)

    bpy.types.Object.ignores_none = bpy.props.BoolProperty(default=False)
    bpy.types.Object.ignores_walls = bpy.props.BoolProperty(default=False)
    bpy.types.Object.ignores_objects = bpy.props.BoolProperty(default=False)
    bpy.types.Object.ignores_sims = bpy.props.BoolProperty(default=False)
    bpy.types.Object.ignores_roofs = bpy.props.BoolProperty(default=False)
    bpy.types.Object.ignores_fences = bpy.props.BoolProperty(default=False)
    bpy.types.Object.ignores_modular_stairs = bpy.props.BoolProperty(default=False)
    bpy.types.Object.ignores_objects_of_same_type = bpy.props.BoolProperty(default=False)
    bpy.types.Object.ignores_columns = bpy.props.BoolProperty(default=False)

    bpy.types.Object.ignores_reserved_space = bpy.props.BoolProperty(default=False)
    bpy.types.Object.ignores_foundations = bpy.props.BoolProperty(default=False)
    bpy.types.Object.ignores_fenestration_node = bpy.props.BoolProperty(default=False)
    bpy.types.Object.ignores_trim = bpy.props.BoolProperty(default=False)
    bpy.types.Object.balance = bpy.props.FloatProperty(default=0, soft_min=0, soft_max=1)

    # One for IK, zero for fk
    bpy.types.Object.l_hand_fk_ik = FloatProperty(default=0, soft_min=0, soft_max=1)
    bpy.types.Object.r_hand_fk_ik = FloatProperty(default=0, soft_min=0, soft_max=1)

    bpy.types.Object.l_foot_fk_ik = FloatProperty(default=0, soft_min=0, soft_max=1)
    bpy.types.Object.r_foot_fk_ik = FloatProperty(default=0, soft_min=0, soft_max=1)
    bpy.types.Object.disable_rig_suffix = bpy.props.BoolProperty(default=False)

    bpy.types.Object.ik_idx = IntProperty(default=0)

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

    bpy.types.Object.ik_targets = CollectionProperty(type=IKTarget)
    bpy.types.Object.ik_idx = IntProperty(default=0)
    bpy.types.Object.rig_name = bpy.props.StringProperty()
    bpy.types.Object.reset_initial_offset_t = bpy.props.StringProperty()
    bpy.types.Object.allow_jaw_animation_for_entire_animation = bpy.props.BoolProperty(default=False)
    bpy.types.Object.explicit_namespaces = bpy.props.StringProperty()
    bpy.types.Object.reference_namespace_hash = bpy.props.StringProperty()
    bpy.types.Object.initial_offset_q = bpy.props.StringProperty()
    bpy.types.Object.initial_offset_t = bpy.props.StringProperty()
    bpy.types.Object.snap_events = bpy.props.StringProperty()
    bpy.types.Object.additional_snap_frames = bpy.props.StringProperty()
    bpy.types.Object.visibility_events = bpy.props.StringProperty()
    bpy.types.Object.base_rig = bpy.props.StringProperty()
    bpy.types.Object.world_rig = bpy.props.StringProperty()
    bpy.types.Object.world_bone = bpy.props.StringProperty()
    bpy.types.Object.use_world_bone_as_root = bpy.props.BoolProperty(default=False)

    bpy.types.Object.relative_rig = bpy.props.StringProperty(update=update_initial_offsets)
    bpy.types.Object.relative_bone = bpy.props.StringProperty(update=update_initial_offsets)
    bpy.types.Object.use_full_precision = bpy.props.BoolProperty(default=False)

    # bpy.types.Object.script_idx = IntProperty(name="Index for my_list", default=0)
    # bpy.types.Object.sound_idx = IntProperty(name="Index for sound_idx", default=0)
    bpy.types.Object.actor_idx = IntProperty(name="Index for actors", default=0)
    bpy.types.Object.state_idx = IntProperty(name="Index for state", default=0)
    bpy.types.Object.controller_idx = IntProperty(name="Index for state", default=0)
    bpy.types.Object.posture_idx = IntProperty(name="Index for state", default=0)
    bpy.types.Object.state_connection_idx = IntProperty(name="Index for state", default=0)

    #  bpy.types.Object.clip_idx = IntProperty(name="Index for clip", default=0)
    bpy.types.Object.is_overlay = bpy.props.BoolProperty(default=False)

    bpy.types.Scene.watcher_running = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.clip_name = bpy.props.StringProperty()
    bpy.types.Scene.clip_name_prefix = bpy.props.StringProperty()
    bpy.types.Scene.clip_splits = bpy.props.StringProperty()

    bpy.types.Scene.footprint_name = bpy.props.StringProperty()

    bpy.types.Scene.s4animtools_export_path = bpy.props.StringProperty()

    actor_types = (("sim", "Sim", "This actor is a sim."), ("object", "Object", "This actor is an object."), ("prop", "Prop", "This actor is a prop."))


    bpy.types.Object.is_s4_actor = bpy.props.BoolProperty(default=False)
    # Actor type can be sim, object, or prop
    bpy.types.Object.actor_type = bpy.props.EnumProperty(items = actor_types)
    bpy.types.Object.is_enabled_for_animation = bpy.props.BoolProperty(default=False)
    bpy.types.Object.show_footprint_options = bpy.props.BoolProperty(default=False)
    bpy.types.Object.show_mirror_and_masking_options = bpy.props.BoolProperty(default=False)
    bpy.types.Object.show_ik_options = bpy.props.BoolProperty(default=False)
    bpy.types.Object.show_events = bpy.props.BoolProperty(default=False)
    bpy.types.Object.show_clip_options = bpy.props.BoolProperty(default=False)
    bpy.types.Object.show_initial_offset_options = bpy.props.BoolProperty(default=False)

    bpy.types.Object.show_experimental_options = bpy.props.BoolProperty(default=False)
    bpy.types.Object.is_sim_skin = bpy.props.BoolProperty(default=False)
    bpy.types.Object.active_sim_skin = bpy.props.EnumProperty(items=update_valid_skins, update=update_active_sim_skin)

    bpy.types.Object.allow_slots = bpy.props.BoolProperty(default=False)

    # 60 FPS downsample to 30
    bpy.types.Scene.downsample_60_to_30 = bpy.props.BoolProperty(default=False)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        try:
            unregister_class(cls)
        except:
            pass
    for ik_idx in range(-1, 11):
        pos, rot = getattr(bpy.types.PoseBone, f"ik_pos_{ik_idx}"), getattr(bpy.types.PoseBone, f"ik_rot_{ik_idx}")
        del pos
        del rot

    del bpy.types.Object.l_hand_fk_ik
    del bpy.types.Object.r_hand_fk_ik
    del bpy.types.Object.l_foot_fk_ik
    del bpy.types.Object.r_foot_fk_ik

    del bpy.types.Object.ik_targets
    del bpy.types.Object.ik_idx
    del bpy.types.Object.rig_name
    del bpy.types.Object.reset_initial_offset_t
    del bpy.types.Object.parent_events
    del bpy.types.Object.sound_events
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
    del bpy.types.Object.reaction_events
    del bpy.types.Object.play_effect_events
    del bpy.types.Object.stop_effect_events
    del bpy.types.Object.disable_lipsync_events

    # bpy.types.Object.script_idx = IntProperty(name="Index for my_list", default=0)
    # bpy.types.Object.sound_idx = IntProperty(name="Index for sound_idx", default=0)
    # bpy.types.Object.actor_idx = IntProperty(name="Index for actors", default=0)
    # bpy.types.Object.state_idx = IntProperty(name="Index for state", default=0)
    #  bpy.types.Object.clip_idx = IntProperty(name="Index for clip", default=0)
    del bpy.types.Scene.is_overlay

    del bpy.types.Scene.watcher_running
    del bpy.types.Scene.clip_name
    del bpy.types.Scene.clip_name_prefix
    del bpy.types.Scene.clip_splits

    del bpy.types.Object.is_s4_actor
    del bpy.types.Object.actor_type
    del bpy.types.Object.is_enabled_for_animation
    del bpy.types.Object.show_footprint_options
    del bpy.types.Object.show_mirror_and_masking_options
    del bpy.types.Object.show_ik_options
    del bpy.types.Object.show_experimental_options
    del bpy.types.Object.is_sim_skin
    del bpy.types.Object.allow_slots