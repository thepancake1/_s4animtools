import bpy
import os
import time
import math
import importlib
from _s4animtools.serialization.fnv import get_64bithash
from _s4animtools.rig_constants import grips, grips_mapping
from _s4animtools.rig_tools import ExportRig, SyncRigToMesh
from _s4animtools.events.events import SnapEvent, SoundEvent, ScriptEvent, ReactionEvent, VisibilityEvent, ParentEvent, \
    PlayEffectEvent, FocusCompatibilityEvent, SuppressLipsyncEvent, StopEffectEvent
from _s4animtools.serialization.types.basic import Float32, UInt32
from _s4animtools.clip_processing.clip_header import ClipResource, bone_to_slot_offset_idx
from _s4animtools.ik_baker import s4animtool_OT_bakeik, get_ik_targets
from _s4animtools.asm.state_machine import ActorPanel, ActorProperties, LIST_OT_MoveActor, LIST_OT_NewActor, \
    LIST_OT_DeleteActor
from _s4animtools.asm.states import StateProperties, LIST_OT_NewState, LIST_OT_DeleteState, LIST_OT_MoveState, \
    StatePanel, ControllerProperties, LIST_OT_NewController, LIST_OT_RemoveController, LIST_OT_MoveControllerState, \
    PostureProperties, PosturePanel, LIST_OT_NewPosture, LIST_OT_DeletePosture, LIST_OT_MovePosture, StateConnections, \
    LIST_OT_NewStateConnection, LIST_OT_DeleteStateConnection, LIST_OT_MoveStateConnection
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector, Quaternion
from bpy.props import IntProperty, CollectionProperty, FloatProperty
from bpy.types import PropertyGroup
from collections import defaultdict
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
    CopySelectedLeftSideToRightSide, CopyLeftSideAnimationToRightSideSim, CopyBakedAnimationToControlRig
from _s4animtools.ik_manager import BeginIKMarker, LIST_OT_NewIKTarget,LIST_OT_CreateIKTarget, LIST_OT_DeleteIKTarget, LIST_OT_MoveIKTarget, \
    s4animtool_OT_removeIK, s4animtool_OT_mute_ik, s4animtool_OT_unmute_ik, LIST_OT_NewIKRange, LIST_OT_DeleteIKRange, \
    LIST_OT_DeleteSpecificIKTarget, MAX_SUBROOTS
import _s4animtools.animation_exporter.animation
from _s4animtools.animation_exporter.animation import AnimationExporter
import _s4animtools.rig.create_rig
from _s4animtools.serialization.types.transforms import Vector3, Quaternion
import _s4animtools.clip_processing.clip_body
import _s4animtools.clip_processing.f1_palette

CHAIN_STR_IDX = 2
bl_info = {"name": "_s4animtools", "category": "Object", "blender": (2, 80, 0)}
importlib.reload(_s4animtools.animation_exporter.animation)
importlib.reload(_s4animtools.clip_processing.f1_palette)
importlib.reload(_s4animtools.frames.frame)
importlib.reload(_s4animtools.clip_processing.clip_body)
importlib.reload(_s4animtools.channels.palette_channel)

# importlib.reload(_s4animtools.asm.state_machine)
# importlib.reload(_s4animtools.translation_channel)
# importlib.reload(_s4animtools.f1_normalized_channel)
# importlib.reload(_s4animtools.rig.create_rig)

importlib.reload(_s4animtools.clip_processing.clip_header)
importlib.reload(_s4animtools.control_rig.basic_control_rig)
importlib.reload(_s4animtools.ik_manager)
importlib.reload(_s4animtools.clip_processing.clip_body)

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
    if scale == 0:
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


class ClipExporter(bpy.types.Operator):
    bl_idname = "s4animtools.export_clip"
    bl_label = "Export Clip"
    bl_options = {"REGISTER", "UNDO"}

    def convert_into_value(self, value):
        return str(value)

    def get_distance(self, posA, posB):
        distance = math.sqrt((posA.x - posB.x) ** 2 + (posA.y - posB.y) ** 2 + (posA.z - posB.z) ** 2)
        # print(distance)
        return distance

    def get_keyframes(self, obj):
        keyframes = []
        anim = obj.animation_data
        if anim is not None and anim.action is not None:
            for fcu in anim.action.fcurves:
                for keyframe in fcu.keyframe_points:
                    x, y = keyframe.co
                    if x not in keyframes:
                        keyframes.append((math.ceil(x)))
        return keyframes

    def setup_events(self, context, current_clip, start_frame, frame_count, additional_snap_frames):
        """
        Shifts the timestamps of the clip events depending on the split.
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
                try:
                    original_timestamp = parameters[0].strip()
                    original_timestamp, timeshifted_timestamp = self.create_timeshifted_timestamp(original_timestamp,
                                                                                                  start_time)
                    if event == SnapEvent:
                        snap_frames.append(original_timestamp)
                    if event == FocusCompatibilityEvent:
                        if frame_time >= timeshifted_timestamp >= 0:
                            _, timeshifted_end_timestamp = self.create_timeshifted_timestamp(parameters[1].strip(),
                                                                                             start_time)
                            current_clip.add_event(
                                event(timeshifted_timestamp, timeshifted_end_timestamp, *parameters[2:]))

                    else:
                        if frame_time >= timeshifted_timestamp >= 0:
                            current_clip.add_event(event(timeshifted_timestamp, *parameters[1:]))
                except Exception as e:
                    print(e)
                    #raise Exception("You're missing parameters for your event..")

        if additional_snap_frames != "":
            additional_snap_frames = additional_snap_frames.split(",")
            for frame in additional_snap_frames:
                original_frame = int(frame)
                timeshifted_frame = original_frame - start_frame
                if frame_count > timeshifted_frame >= 0:
                    snap_frames.append(timeshifted_frame)
        return snap_frames

    def create_timeshifted_timestamp(self, original_timestamp, start_time):
        if original_timestamp.endswith("f"):
            original_timestamp = float(original_timestamp[:-1]) / 30
        else:
            original_timestamp = float(original_timestamp)
        timeshifted_timestamp = original_timestamp - start_time
        return original_timestamp, timeshifted_timestamp

    def execute(self, context):
        t1 = time.time()

        root_bone = list(bpy.context.active_object.pose.bones)[0]
        world_root_bone, world_rig = self.determine_world_ik(context, root_bone)

        ik_targets = determine_ik_slot_targets(bpy.context.active_object)
        weight_channels = []
        slot_assignments = defaultdict(list)
        # add rigs namespaces
        rigs_used = []
        ik_bones = []
        animated_bones = dict()
        previous_recorded_frame = dict()

        def setup_channel_data(bone):

            default_bone_channels = {"Main Channel": {"TRANSLATION": {}, "ORIENTATION": {}, "SCALE": {}},
                                     "IK World Channel": {"TRANSLATION": {}, "ORIENTATION": {}}}
            animated_bones[bone.name] = default_bone_channels.copy()
            default_previous_frame = {
                "Main Channel": {"TRANSLATION": Vector((0, 0, 0)), "ORIENTATION": Quaternion((1, 0, 0, 0)),
                                 "SCALE": Vector((1, 1, 1))},
                "IK World Channel": {"TRANSLATION": Vector((0, 0, 0)), "ORIENTATION": Quaternion((1, 0, 0, 0))}}
            previous_recorded_frame[bone.name] = default_previous_frame.copy()

            for ik_chain in slot_assignments:
                if ik_chain == bone.name:
                    for idx in range(len(slot_assignments[ik_chain])):
                        channel_name = "IK Target {} Channel".format(1 + idx)
                        animated_bones[bone.name][channel_name] = {"TRANSLATION": {}, "ORIENTATION": {}}
                        previous_recorded_frame[bone.name][channel_name] = {"TRANSLATION": Vector((0, 0, 0)),
                                                                            "ORIENTATION": Quaternion((1, 0, 0, 0))}

            for child in bone.children:
                setup_channel_data(child)

        snap_frames = None
        # Todo why doesn't this use the Slot Assignment class?
        for bone in constraints:
            for idx, target in enumerate(constraints[bone]):
                slot_assignments[bone].append(
                    (bone, target[0], target[1], idx, int(target[2].target.name.split(" ")[2])))
                if bone not in ik_bones:
                    ik_bones.append(bone)
        # Ik bones list
        # Get blend name for source file name in clip file.
        filepath = bpy.data.filepath
        blend_name = filepath.split(os.sep)[-1]

        clip_indices = [0, ]
        clip_splits = context.scene.clip_splits.split(",")
        if len(clip_splits) > 0:
            for idx in range(len(clip_splits)):
                clip_indices.append(int(clip_splits[idx]))

        # clip_indices.append(bpy.context.scene.frame_end)

        def finalize_channels(all_frame_data, channel_data, current_channel):
            min, max = 9999, -9999
            for idx, frame_data in channel_data.items():
                all_frame_data[idx] = frame_data.copy()
                for value in frame_data:
                    # print(value, max)
                    if max < value:
                        max = value
                    if min > value:
                        min = value
                # TODO Uhhh does the below code even do what it's supposed to do?
            # printfor ax_idx in range(len(frame_data)):
            #     frame_data[ax_idx] = number_format(frame_data[ax_idx])
            offset = (min + max) / 2
            scale = -((min - max) / 2)
            current_channel.set_channel_data(offset=offset, scale=scale, individual_frames=all_frame_data,
                                             snap_frames=snap_frames)
            current_clip.clip_body.add_channel(current_channel)

        def recursive_bone_animate(bone, idx, is_snap_frame):
            if bone.parent and keyframed_bones[
                bone.name] and bpy.context.scene.is_overlay or not bpy.context.scene.is_overlay and bone.parent:
                # Animate relative to the world rig if the current bone is the b__ROOT_bind__ bone.
                if bone.parent.name == "b__ROOT__":
                    animate_relative_to_bone(bone, world_root_bone, bpy.context.active_object, world_rig, idx,
                                             "Main Channel", is_snap_frame)
                else:
                    animate_relative_to_bone(bone, bone.parent, bpy.context.active_object, bpy.context.active_object,
                                             idx, "Main Channel", is_snap_frame)

                use_IK = True
                if bone.name in ik_bones and use_IK:
                    current_ik_target = 0
                    animate_relative_to_bone(bone, world_root_bone, bpy.context.active_object, world_rig, idx,
                                             "IK World Channel", is_snap_frame)
                    current_ik_target += 1

                    for bone_constraint_name in slot_assignments.keys():
                        if bone.name == bone_constraint_name:
                            for bone_constraint in slot_assignments[bone_constraint_name]:
                                channel_name = "IK Target {} Channel".format(current_ik_target)
                                current_ik_target += 1
                                animate_relative_to_bone(bone, bone_constraint[1].pose.bones[bone_constraint[2]],
                                                         bpy.context.active_object, bone_constraint[1], idx,
                                                         channel_name, is_snap_frame)
            for child in bone.children:
                # Don't animate slots.
                if "slot" not in child.name:
                    recursive_bone_animate(child, idx, is_snap_frame)

        def recursive_bone_finalize(bone):
            current_sequence_count = 1  # This affects the actual IK translation and rotation offset data
            for channel_name, channel_bundle in animated_bones[bone.name].items():
                for channel_type, channel_data in channel_bundle.items():
                    # Don't need to save channel if nothing is in it
                    if len(channel_data) == 0:
                        continue

                    all_frame_data = {}
                    current_channel = None
                    if channel_type == "TRANSLATION":
                        current_channel = _s4animtools.channels.translation_channel.Vector3Channel(bone.name, 18, 1)
                    elif channel_type == "ORIENTATION":
                        current_channel = _s4animtools.channels.channel.QuaternionChannel(bone.name, 20, 2)
                    elif channel_type == "SCALE":
                        current_channel = _s4animtools.channels.translation_channel.Vector3Channel(bone.name, 18, 3)
                    if "IK" in channel_name:
                        if channel_type == "TRANSLATION":
                            current_channel = _s4animtools.channels.translation_channel.Vector3Channel(bone.name,
                                                                                                       18, 23 + (
                                                                                                                   current_sequence_count * 2))
                        elif channel_type == "ORIENTATION":
                            current_channel = _s4animtools.channels.channel.QuaternionChannel(bone.name, 20,
                                                                                              (24 + current_sequence_count * 2))
                    finalize_channels(all_frame_data, channel_data, current_channel)
                if "IK" in channel_name:
                    current_sequence_count += 1

            for bone in bone.children:
                recursive_bone_finalize(bone)

        def animate_relative_to_bone(bone, parent_bone, source_rig, target_rig, idx, channel_name, is_snap_frame,
                                     allow_fail_on_scale=True):
            bp1 = source_rig.matrix_world @ bone.matrix
            bp2 = target_rig.matrix_world @ parent_bone.matrix
            matrix_data = bp2.inverted() @ bp1
            rotation_data = matrix_data.to_quaternion()
            translation_data = matrix_data.to_translation()
            last_rotation_data = previous_recorded_frame[bone.name][channel_name]["ORIENTATION"]
            last_translation_data = previous_recorded_frame[bone.name][channel_name]["TRANSLATION"]
            # TODO quick hack for scale
            try:
                scale_data = bone.scale

                last_scale_data = previous_recorded_frame[bone.name][channel_name]["SCALE"]
                if abs(self.get_distance(last_scale_data, scale_data)) < 0.00001 and len(
                        animated_bones[bone.name][channel_name]["SCALE"].keys()) >= 1 and not is_snap_frame:
                    pass
                else:
                    animated_bones[bone.name][channel_name]["SCALE"][idx] = [scale_data.x, scale_data.y,
                                                                             scale_data.z]
                    previous_recorded_frame[bone.name][channel_name]["SCALE"] = scale_data.copy()


            except Exception as e:
                if allow_fail_on_scale:
                    pass
                else:
                    raise e
            if abs((last_rotation_data - rotation_data).magnitude) < 0.00001 and len(
                    animated_bones[bone.name][channel_name]["ORIENTATION"].keys()) >= 1 and not is_snap_frame:
                pass
            else:
                animated_bones[bone.name][channel_name]["ORIENTATION"][idx] = [rotation_data.x, rotation_data.y,
                                                                               rotation_data.z,
                                                                               rotation_data.w]
                previous_recorded_frame[bone.name][channel_name]["ORIENTATION"] = rotation_data
            if abs(self.get_distance(last_translation_data, translation_data)) < 0.00001 and len(
                    animated_bones[bone.name][channel_name]["TRANSLATION"].keys()) >= 1 and not is_snap_frame:
                pass
            else:
                animated_bones[bone.name][channel_name]["TRANSLATION"][idx] = [translation_data.x, translation_data.y,
                                                                               translation_data.z]
                previous_recorded_frame[bone.name][channel_name]["TRANSLATION"] = translation_data

        def save_locomotion_data(clip_start, clip_end):
            next_initial_translation_offset = ""
            if "loco" in bpy.context.active_object.pose.bones:
                loco_bone = bpy.context.active_object.pose.bones["loco"]
                # current_clip.clip_body._f1PaletteData.append(float32(0))

                for idx in range(clip_start, clip_end):
                    bpy.context.scene.frame_set(idx)
                    bp1 = bpy.context.active_object.matrix_world @ loco_bone.matrix

                    current_clip.clip_body._f1PaletteData.append(Float32(round(abs(bp1.to_translation().y), 6)))
                    if idx == clip_start:
                        next_initial_translation_offset = "0,0,{}".format(abs(bp1.to_translation().y))
                current_clip.clip_body._f1PaletteSize = len(current_clip.clip_body._f1PaletteData)
                loco_channel_pos = _s4animtools.channels.palette_channel.PaletteTranslationChannel("loco", 3, 1)
                channel_frame_data = {}
                for idx in range(clip_start, clip_end):
                    channel_frame_data[idx - clip_start] = (0, 0, idx - clip_start)
                loco_channel_pos.set_channel_data(0, 1, channel_frame_data, snap_frames)
                loco_channel_rot = _s4animtools.channels.channel.QuaternionChannel("loco", 17, 2)
                loco_channel_rot.set_channel_data(0, 1, {}, snap_frames)

                loco_channel_pos._target = UInt32(720414894)
                loco_channel_rot._target = UInt32(720414894)
                loco_channel_pos._frame_count = current_clip.clip_body._f1PaletteSize
                current_clip.clip_body.add_channel(loco_channel_pos)

                current_clip.clip_body.add_channel(loco_channel_rot)
            return next_initial_translation_offset

        def get_animated_bones():
            rig = bpy.context.active_object.pose
            keyframed_bones = defaultdict(bool)
            for b in rig.bones:
                for fcu in bpy.context.active_object.animation_data.action.fcurves:
                    if fcu.data_path.startswith('pose.bones["{}"]'.format(b.name)):
                        keyframed_bones[b.name] = True
                        break
            return keyframed_bones

        keyframed_bones = get_animated_bones()

        clip_names = []
        clip_input_names = context.scene.clip_name.split(",")
        if len(clip_input_names) > 0:
            for idx in range(len(clip_input_names)):
                clip_names.append(clip_input_names[idx].strip())

        reset_offset = []
        if context.object.reset_initial_offset_t != "":
            reset_initial_offset_t = context.object.reset_initial_offset_t.split(",")
            if len(reset_initial_offset_t) > 0:
                for idx in range(len(reset_initial_offset_t)):
                    reset_offset.append(reset_initial_offset_t[idx].strip() == "+")
        else:
            for clip_idx in range(len(clip_indices) - 1):
                reset_offset.append(False)

        initial_offset_t = context.object.initial_offset_t
        initial_offset_q = context.object.initial_offset_q
        # Set the initial offsets to the default if the user doesn't enter anything.
        if initial_offset_t == "":
            initial_offset_t = "0,0,0"
        if initial_offset_q == "":
            initial_offset_q = "0,0,0,1"
        rig_name = context.object.rig_name
        if rig_name == "":
            context.object.rig_name = "x"
            rig_name = context.object.rig_name

        reference_namespace_hash = context.object.reference_namespace_hash
        if reference_namespace_hash == "":
            reference_namespace_hash = 0
        else:
            reference_namespace_hash = int(reference_namespace_hash, 16)

        for clip_idx in range(len(clip_indices) - 1):
            clip_frame_idx = clip_indices[clip_idx]
            if context.scene.clip_name_prefix == "":
                combined_clip_name = "{}".format(clip_names[clip_idx])
            else:
                combined_clip_name = "{}_{}".format(context.scene.clip_name_prefix, clip_names[clip_idx])
            has_loco_bone = "loco" in context.object.pose.bones
            current_clip = ClipResource(combined_clip_name, rig_name, slot_assignments,
                                        context.object.explicit_namespaces,
                                        reference_namespace_hash, Quaternion.from_str(initial_offset_q),
                                        Vector3.from_str(initial_offset_t), blend_name, has_loco_bone,
                                        context.object.disable_rig_suffix)
            setup_channel_data(root_bone)

            clip_start, clip_end = clip_frame_idx, clip_indices[clip_idx + 1]

            snap_frames = self.setup_events(context, current_clip, clip_start, clip_end - clip_start,
                                            context.object.additional_snap_frames)

            for channel in weight_channels:
                current_clip.clip_body.add_channel(channel)
            last_frame_influences = defaultdict(int)
            ik_weight_animation_data = defaultdict(dict)

            for current_frame in range(clip_start, clip_end):
                bpy.context.scene.frame_set(current_frame)
                bpy.context.view_layer.update()

                # Clip data needs to be offset when the clip actually starts is at zero.
                recursive_bone_animate(root_bone, current_frame - clip_start, current_frame - clip_start in snap_frames)
                for bone in constraints:
                    for idx, target in enumerate(constraints[bone]):
                        ik_weight = gather_ik_weights(ik_weight_animation_data, target[2], clip_start, current_frame,
                                                      last_frame_influences[target[2]])
                        last_frame_influences[target[2]] = ik_weight
            for bone in constraints:
                for idx, target in enumerate(constraints[bone]):
                    current_clip.clip_body.add_channel(
                        (create_ik_weight_channels(bone, ik_weight_animation_data[target[2]], idx + 1)))

            next_initial_translation_offset = save_locomotion_data(clip_start, clip_end)
            if next_initial_translation_offset != "":
                # TODO Hack!! Fix this
                current_clip._initialOffsetT = list(map(float, next_initial_translation_offset.split(",")))

            if len(reset_offset) > clip_idx:
                if reset_offset[clip_idx]:
                    initial_offset_t = "0,0,0"
                    initial_offset_q = "0,0,0,1"

            loco_animation = False
            root_bone = bpy.context.active_object.pose.bones["b__ROOT__"]

            if loco_animation:
                try:
                    for bone in self.IK_bones:
                        # todo don't play the animation each time for a bone!!
                        current_clip.clip_body.add_channel(set_loco_world_ik(bone, clip_start, clip_end))
                except:
                    print("wtf")

            recursive_bone_finalize(root_bone)

            current_clip.clip_body.set_clip_length(clip_end - clip_start)

            current_clip.update_duration(clip_end - clip_start)
            current_clip.serialize()
            current_clip = None
        t2 = time.time()
        print(f"Took {t2 - t1} seconds for clip export")

    def determine_world_ik(self, context, root_bone):
        if context.object.world_rig == "":
            world_rig = bpy.context.active_object
            world_root_bone = root_bone
        else:
            world_rig = bpy.data.objects[context.object.world_rig]
            world_root_bone = world_rig.pose.bones[context.object.world_bone]
        return world_root_bone, world_rig

    def invoke(self, context, event):

        self.execute(context)

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
                original_timestamp, timeshifted_timestamp = self.create_timeshifted_timestamp(original_timestamp,
                                                                                              start_time)
                if event == SnapEvent:
                    snap_frames.append(original_timestamp)
                if event == FocusCompatibilityEvent:
                    if frame_time >= timeshifted_timestamp >= 0:
                        _, timeshifted_end_timestamp = self.create_timeshifted_timestamp(parameters[1].strip(),
                                                                                         start_time)
                        current_clip.add_event(
                            event(timeshifted_timestamp, timeshifted_end_timestamp, *parameters[2:]))

                else:
                    if frame_time >= timeshifted_timestamp >= 0:
                        current_clip.add_event(event(timeshifted_timestamp, *parameters[1:]))

#                    raise Exception("You're missing parameters for your event..")

        if additional_snap_frames != "":
            additional_snap_frames = additional_snap_frames.split(",")
            for frame in additional_snap_frames:
                original_frame = int(frame)
                timeshifted_frame = original_frame - start_frame
                if frame_count > timeshifted_frame >= 0:
                    snap_frames.append(timeshifted_frame)
        return snap_frames

    def create_timeshifted_timestamp(self, original_timestamp, start_time):
        if original_timestamp.endswith("f"):
            original_timestamp = float(original_timestamp[:-1]) / 30
        else:
            original_timestamp = float(original_timestamp)
        timeshifted_timestamp = original_timestamp - start_time
        return original_timestamp, timeshifted_timestamp

    def get_clip_names(self):
        clip_names = []
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
        if len(clip_splits) > 0:
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
                             initial_offset_q=Quaternion.from_str(initial_offset_q),
                             initial_offset_t=Vector3.from_str(initial_offset_t), rig_name=rig_name))
            self.clip_infos = clip_infos
        return self.clip_infos

    def execute(self, context):
        t1 = time.time()
        self.context = context
        self.clip_infos = []

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

        for idx, clip_info in enumerate(self.clip_infos):
            current_clip = ClipResource(clip_info.name, clip_info.rig_name, ik_targets_to_bone,
                                        clip_info.explicit_namespaces,
                                        clip_info.reference_namespace_hash, clip_info.initial_offset_q,
                                        clip_info.initial_offset_t, source_filename, False, context.object.disable_rig_suffix)
            rig = self.context.object
            snap_frames = self.setup_events(self.context, current_clip, clip_info.start_frame, clip_info.end_frame - clip_info.start_frame,
                                            self.context.object.additional_snap_frames)


            exporter = AnimationExporter(rig, snap_frames, world_rig=world_rig, world_root=world_root, use_full_precision=self.context.object.use_full_precision)
            exporter.create_animation_data()
            exporter.paletteHolder.try_add_palette_to_palette_values(0)
            exporter.paletteHolder.try_add_palette_to_palette_values(1.0)

            last_frame_influences = defaultdict(int)
            ik_weight_animation_data = defaultdict(dict)

            slot_assignment_source_bones = ik_targets_to_bone.keys()

            for frame_idx in range(clip_info.start_frame, clip_info.end_frame):
                bpy.context.scene.frame_set(frame_idx)
                bpy.context.view_layer.update()
                exporter.animate_recursively(frame_idx, start_frame=clip_info.start_frame, force=frame_idx == clip_info.start_frame
                                                              or frame_idx == clip_info.end_frame)

                for source_bone_ik in slot_assignment_source_bones:
                    for ik_idx, slot_assignment_info in enumerate(ik_targets_to_bone[source_bone_ik]):

                        ik_weight = gather_ik_weights(rig, ik_weight_animation_data, slot_assignment_info.source_bone, ik_idx, clip_info.start_frame,
                                                      frame_idx, last_frame_influences[(slot_assignment_info.source_bone, ik_idx)])
                        last_frame_influences[(slot_assignment_info.source_bone, ik_idx)] = ik_weight

            for source_bone_ik in slot_assignment_source_bones:
                for ik_idx, slot_assignment_info in enumerate(ik_targets_to_bone[source_bone_ik]):
                    exporter.add_baked_animation_data_to_frame(slot_assignment_info.source_bone,
                                                               start_frame=clip_info.start_frame,
                                                               end_frame=clip_info.end_frame, ik_idx=ik_idx)
                    current_clip.clip_body.add_channel(
                        (create_ik_weight_channels(slot_assignment_info.source_bone,
                                                   ik_weight_animation_data[(slot_assignment_info.source_bone, ik_idx)],
                                                   ik_idx)))

            for channel in exporter.export_to_channels():
                current_clip.clip_body.add_channel(new_channel=channel)
            current_clip.clip_body.set_palette_values(exporter.paletteHolder.palette_values)
            current_clip.clip_body.set_clip_length(clip_info.end_frame - clip_info.start_frame)
            current_clip.update_duration(clip_info.end_frame - clip_info.start_frame)

            current_clip.serialize()
        t2 = time.time()
        print(f"Took {t2 - t1} seconds for clip export")
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

    def draw_events(self, obj, events_list_name, x_scale, description, event_name, layout):
        events_list = getattr(obj, events_list_name)
        layout.label(
            text=f"{event_name}: {len(events_list)} - {description}")
        for idx, item in enumerate(events_list):
            row = layout.row()
            row2 = row.row()
            row.scale_x = x_scale

            row2.prop(item, "info", text="")
            row.operator('s4animtools.move_new_element', text='Up').args = f"{events_list_name},{idx},up"
            row.operator('s4animtools.move_new_element', text='Down').args = f"{events_list_name},{idx},down"
            row.operator('s4animtools.move_new_element', text='Delete').args = f"{events_list_name},{idx},delete"
            row.operator('s4animtools.move_new_element', text='Create').args = f"{events_list_name},{idx},create"

    def draw(self, context):
        self.layout.operator("s4animtools.copy_baked_animation", icon='MESH_CUBE', text="Copy Baked Animation")

        # self.layout.operator("s4animtools.copy_left_side", icon='MESH_CUBE', text="Copy Left Side (Bed)")
        self.layout.operator("s4animtools.copy_left_side_sim", icon='MESH_CUBE', text="Flip Sim")
        # self.layout.operator("s4animtools.copy_left_side_sim_selected", icon='MESH_CUBE', text="Copy Left Side (Sim) Selected")
        self.layout.operator("s4animtools.maintain_keyframe", icon="MESH_CUBE",
                             text="Maintain Keyframe").direction = "FORWARDS"
        self.layout.operator("s4animtools.maintain_keyframe", icon="MESH_CUBE",
                             text="Maintain Keyframe Backward").direction = "BACK"

        # self.layout.operator("s4animtools.create_advanced_control_rig", icon='MESH_CUBE', text="Create Advanced Control Rig (Sim)")

        self.layout.operator("s4animtools.import_rig", icon='MESH_CUBE', text="Import Rig")
        self.layout.label(text="Use Full Precision means using full precision for all animation data.")
        self.layout.label(text="Don't enable if you don't know what that means!")

        self.layout.prop(context.object, "use_full_precision", text="EXPERIMENTAL!! Use Full Precision")
        self.layout.operator("s4animtools.new_export_clip", icon='MESH_CUBE', text="Export Clip")

        self.layout.operator("s4animtools.export_rig", icon='MESH_CUBE', text="Export Rig")

        #self.layout.operator("s4animtools.export_clip", icon='MESH_CUBE', text="Export Clip")

        # self.layout.operator("s4animtools.sync_rig_to_mesh", icon='MESH_CUBE', text="Sync Rig To Mesh")
        # self.layout.prop(context.scene, "IK_bone_target")  # String for displaying current IK bone
        row = self.layout.row()
        # row.operator("s4animtools.beginikmarker", text="Add Left Hand").command = "LEFT,HAND,BEGIN"
        # row.operator("s4animtools.beginikmarker", text="Remove Left Hand").command = "LEFT,HAND,END"
        #
        # row = self.layout.row()
        # row.operator("s4animtools.beginikmarker", text="Add Right Hand").command = "RIGHT,HAND,BEGIN"
        # row.operator("s4animtools.beginikmarker", text="Remove Right Hand").command = "RIGHT,HAND,END"
        # row = self.layout.row()
        # row.operator("s4animtools.beginikmarker", text="Add Left Foot").command = "LEFT,FOOT,BEGIN"
        # row.operator("s4animtools.beginikmarker", text="Remove Left Foot").command = "LEFT,FOOT,END"
        # row = self.layout.row()
        # row.operator("s4animtools.beginikmarker", text="Add Right Foot").command = "RIGHT,FOOT,BEGIN"
        # row.operator("s4animtools.beginikmarker", text="Remove Right Foot").command = "RIGHT,FOOT,END"
        # row = self.layout.row()
        #
        # row.operator("s4animtools.beginikmarker", text="Add Root Bind").command = "SINGLE,BIND,BEGIN"
        # row.operator("s4animtools.beginikmarker", text="Remove Root Bind").command = "SINGLE,BIND,END"
        #
        obj = context.object

        if obj is not None:

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

                # if selected_bone.name == "b__L_Hand__IK" or selected_bone.name == "b__L_Hand__":
                #    self.layout.prop(obj, "l_hand_fist", text="Left Hand Fist")
            # self.layout.prop(selected_bone, "mirrored_bone")
            # self.layout.prop(selected_bone, "bone_flags")
            # isnt_mirrored = selected_bone.bone_flags[-3] == "1" and selected_bone.bone_flags[-4] == "1" and selected_bone.bone_flags[-5] == "1"
            # if not isnt_mirrored:
            #    mirrored_status = "-Is Not A Mirrored Bone"
            # else:
            #    mirrored_status = "-Is Mirrored Bone or Single Bone"
            # self.layout.label(text=mirrored_status)

            # movable_status = "-Editable by Sliders"
            # if not  selected_bone.bone_flags[7] == "1":
            #    movable_status = "-Not Editable by Sliders"
            # self.layout.label(text=movable_status)

            # slot_status = "-Not Slot"
            # if  selected_bone.bone_flags[17] == "1":
            #    slot_status = "-Slot"
            # self.layout.label(text=slot_status)

            # animatable_status = "-Not Animatable"
            # if selected_bone.bone_flags[18] == "1":
            #    animatable_status = "-Animatable"
            # self.layout.label(text=animatable_status)

            except Exception as e:
                pass

            self.layout.prop(obj, "l_hand_fk_ik", text="Left Hand FK/IK")

            self.layout.prop(obj, "r_hand_fk_ik", text="Right Hand FK/IK")
            self.layout.prop(obj, "l_foot_fk_ik", text="Left Foot FK/IK")
            self.layout.prop(obj, "r_foot_fk_ik", text="Right Foot FK/IK")

            self.layout.prop(obj, "reset_initial_offset_t", text="Reset Initial Offset T")
            self.layout.prop(obj, "world_rig", text="World Rig")
            self.layout.prop(obj, "world_bone", text="World Bone")
            self.layout.prop(obj, "use_world_bone_as_root", text="Use World Bone As Root")

            self.draw_property_if_not_empty(obj, "parent_events", self.layout)
            self.draw_property_if_not_empty(obj, "sound_events", self.layout)
            self.draw_property_if_not_empty(obj, "script_events", self.layout)
            self.draw_property_if_not_empty(obj, "snap_events", self.layout)
            self.draw_property_if_not_empty(obj, "reaction_events", self.layout)
            self.draw_property_if_not_empty(obj, "play_effect_events", self.layout)
            self.draw_property_if_not_empty(obj, "stop_effect_events", self.layout)
            self.draw_property_if_not_empty(obj, "disable_lipsync_events", self.layout)
            self.draw_events(obj, "parent_events_list", 0.1,
                             "Parameters (Frame Number/Object To Be Parented/Object To Be Parented To/Bone)",
                             "Parent Events", self.layout)
            self.draw_events(obj, "sound_events_list", 0.1, "Parameters (Frame Number/Sound Effect Name)",
                             "Sound Events", self.layout)
            self.draw_events(obj, "script_events_list", 0.1, "Parameters (Frame Number/Script Xevt)", "Script Events",
                             self.layout)
            self.draw_events(obj, "snap_events_list", 0.1, "Parameters (Frame Number/Actor/Translation/Quaternion)",
                             "Snap Events", self.layout)
            self.draw_events(obj, "reaction_events_list", 0.1, "Parameters (Frame Number/Reaction ASM)",
                             "Reaction Events", self.layout)
            self.draw_events(obj, "play_effect_events_list", 0.1,
                             "Parameters (Frame Number/Actor Hash/Bone Name Hash/(always 0)/(almost always 0)/Unique VFX Name)",
                             "Play Effect Events", self.layout)
            self.draw_events(obj, "stop_effect_events_list", 0.1,
                             "Parameters (Frame Number/Unique VFX Name/(always 0)/Unknown Bool 1)",
                             "Stop Effect Events", self.layout)
            self.draw_events(obj, "disable_lipsync_events_list", 0.1, "Parameters (Frame Number/Duration)",
                             "Suppress Lipsync Events", self.layout)
            self.draw_events(obj, "visibility_events_list", 0.1, "Parameters (Frame Number/Actor/Visibility)",
                             "Visibility Events", self.layout)
            self.draw_events(obj, "focus_compatibility_events_list", 0.1, "Parameters (End Frame,Level)",
                             "Focus Compatibility Events", self.layout)

            self.layout.prop(obj, "explicit_namespaces", text="Explicit Namespaces")
            self.layout.prop(obj, "reference_namespace_hash", text="Reference Namespace Hash")
            self.layout.prop(obj, "initial_offset_q", text="Initial Offset Q")
            self.layout.prop(obj, "initial_offset_t", text="Initial Offset T")

            self.layout.prop(obj, "additional_snap_frames", text="Additional Snap Frames")
            self.layout.prop(obj, "rig_name", text="Rig Name")  # String for current clip actor
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

            layout.operator("s4animtools.bakeik", text="Bake IK")
            layout.operator("s4animtools.muteik", text="Mute IK")
            layout.operator("s4animtools.unmuteik", text="Unmute IK")

            layout.operator("s4animtools.removeik", text="Remove IK")
            layout.prop(obj, "relative_rig")
            layout.prop(obj, "relative_bone")
            layout.operator("s4animtools.offset_calculator", text="Offset Calculator")
            layout.operator("s4animtools.initialize_events", text="Initialize Events")

        # self.layout.prop(context.scene, "IK_bone_target")  # String for displaying current IK bone
        self.layout.prop(context.scene, "clip_splits")
        self.layout.prop(context.scene, "clip_name_prefix")  # clip_name_prefix
        self.layout.prop(context.scene, "clip_name")

        self.layout.prop(context.scene, "is_overlay")
        self.layout.prop(obj, "disable_rig_suffix")
        # TODO remove this at some point when compatibility with older files isn't an issue. This used to be
        # when each file could only contain one actor.
        if context.scene.rig_name != "":
            self.layout.prop(context.scene, "reset_initial_offset_t")
            self.layout.prop(context.scene, "world_rig")
            self.layout.prop(context.scene, "world_bone")
            self.layout.prop(context.scene, "parent_events")
            self.layout.prop(context.scene, "sound_events")
            self.layout.prop(context.scene, "explicit_namespaces")
            self.layout.prop(context.scene, "reference_namespace_hash")
            self.layout.prop(context.scene, "initial_offset_q")
            self.layout.prop(context.scene, "initial_offset_t")
            self.layout.prop(context.scene, "snap_events")
            self.layout.prop(context.scene, "additional_snap_frames")
            self.layout.prop(context.scene, "visibility_events")
            self.layout.prop(context.scene, "rig_name")  # String for current clip actor

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

            if item.target_obj is not "":
                target_obj = bpy.data.objects[item.target_obj]
                sub.prop_search(item, "target_bone", target_obj.pose, "bones")
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


class InitializeEvents(bpy.types.Operator):
    bl_idname = "s4animtools.initialize_events"
    bl_label = "Initialize Events"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.object.parent_events_list.add()
        context.object.sound_events_list.add()
        context.object.script_events_list.add()
        context.object.play_effect_events_list.add()

        context.object.stop_effect_events_list.add()
        context.object.disable_lipsync_events_list.add()
        context.object.snap_events_list.add()
        context.object.reaction_events_list.add()
        context.object.visibility_events_list.add()
        context.object.focus_compatibility_events_list.add()
        return {"FINISHED"}


class OffsetCalculator(bpy.types.Operator):
    bl_idname = "s4animtools.offset_calculator"
    bl_label = "Import Rig"
    bl_options = {"REGISTER", "UNDO"}

    def determine_relative_bones(self, context, root_bone):
        if context.object.relative_rig == "":
            relative_rig = bpy.context.active_object
            relative_bone = root_bone
        else:
            relative_rig = bpy.data.objects[context.object.relative_rig]
            relative_bone = relative_rig.pose.bones[context.object.relative_bone]
        return relative_rig, relative_bone

    def execute(self, context):
        active_object_root = bpy.context.active_object.pose.bones["b__ROOT__"]
        relative_rig, relative_bone = self.determine_relative_bones(context, active_object_root)
        chair_matrix = relative_rig.matrix_world @ relative_bone.matrix
        x_matrix = bpy.context.active_object.matrix_world @ active_object_root.matrix
        offset = chair_matrix.inverted() @ x_matrix

       # print(offset.to_translation(), offset.to_quaternion())
        rotation = offset.to_quaternion()
        translation = offset.to_translation()
        bpy.context.active_object.initial_offset_q = ",".join(
            [str(round(rotation[1], 4)), str(round(rotation[2], 4)), str(round(rotation[3], 4)),
             str(round(rotation[0], 4))])
        bpy.context.active_object.initial_offset_t = ",".join(
            [str(round(translation[0], 4)), str(round(translation[1], 4)), str(round(translation[2], 4))])

        return {"FINISHED"}


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


# unused = (ScriptItem, SoundItem, LIST_OT_NewScriptEvent, LIST_OT_MoveScriptEvent, LIST_OT_DeleteScriptEvent,
#          LIST_OT_NewSoundEvent, LIST_OT_MoveSoundEvent, LIST_OT_DeleteSoundEvent,
#          ScriptEventsPanel, SoundEventsPanel, ActorProperties, LIST_OT_NewActor, LIST_OT_DeleteActor,
#          LIST_OT_MoveActor, ActorPanel, LIST_OT_NewState, LIST_OT_DeleteState, LIST_OT_MoveState, StatePanel,
#          ControllerProperties, StateProperties, LIST_OT_NewController, s4animtool_OT_IKEmptyCreator, s4animtool_OT_IKEmptyUpdate, s4animtool_PT_IKProperties,)
classes = (
    Snapper, ExportRig, SyncRigToMesh, ClipExporter,
    S4ANIMTOOLS_PT_MainPanel,
    TimeRange,
    IKTarget, s4animtool_PT_IKTargetPanel, LIST_OT_NewIKTarget, LIST_OT_CreateIKTarget, LIST_OT_DeleteIKTarget, LIST_OT_MoveIKTarget,
    s4animtool_OT_bakeik, s4animtool_OT_removeIK,
    BeginIKMarker, s4animtool_OT_unmute_ik, s4animtool_OT_mute_ik, NewClipExporter, PositionConfig, QuaternionConfig,
    ActorSettings, ClipData, ImportRig, CopyLeftSideAnimationToRightSide, CopyLeftSideAnimationToRightSideSim, CopyBakedAnimationToControlRig,
    CopySelectedLeftSideToRightSide,
    LIST_OT_MoveActor, ActorPanel, LIST_OT_NewState, LIST_OT_DeleteState, LIST_OT_MoveState, StatePanel,
    ActorProperties, ControllerProperties, StateProperties,
    LIST_OT_NewActor, LIST_OT_DeleteActor, LIST_OT_NewController, LIST_OT_RemoveController, LIST_OT_MoveControllerState,
    PosturePanel, PostureProperties,
    LIST_OT_NewPosture, LIST_OT_DeletePosture, LIST_OT_MovePosture, OffsetCalculator, StateConnections,
    LIST_OT_NewStateConnection, LIST_OT_DeleteStateConnection,
    LIST_OT_MoveStateConnection, ExportAnimationStateMachine, MaintainKeyframe, AnimationEvent, InitializeEvents,
    S4ANIMTOOLS_OT_move_new_element, AnimationEvent,
    LIST_OT_NewIKRange, LIST_OT_DeleteIKRange, LIST_OT_DeleteSpecificIKTarget)


def register():
    """Register classes for the things."""
    from bpy.utils import register_class
    for cls in classes:
        try:
            register_class(cls)
        except Exception as e:
            print(e)
    # bpy.types.Object.script_events = CollectionProperty(type=ScriptItem)
    # bpy.types.Object.sound_events = CollectionProperty(type=SoundItem)
    bpy.types.Object.actors = CollectionProperty(type=ActorProperties)
    bpy.types.Object.states = CollectionProperty(type=StateProperties)
    bpy.types.Object.postures = CollectionProperty(type=PostureProperties)
    bpy.types.Object.state_connections = CollectionProperty(type=StateConnections)

    bpy.types.PoseBone.mirrored_bone = bpy.props.StringProperty()
    bpy.types.PoseBone.bone_flags = bpy.props.StringProperty()
    bpy.types.PoseBone.bone_flags = bpy.props.StringProperty()
    for ik_idx in range(-1,11):
        setattr(bpy.types.PoseBone, f"ik_pos_{ik_idx}", bpy.props.FloatVectorProperty(size=3))
        setattr(bpy.types.PoseBone, f"ik_rot_{ik_idx}", bpy.props.FloatVectorProperty(default=(0,0,0,1), size=4, min=-1, max=1))
        setattr(bpy.types.PoseBone, f"ik_weight_{ik_idx}", bpy.props.FloatProperty(min=0, max=1))


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
    bpy.types.Object.parent_events = bpy.props.StringProperty()
    bpy.types.Object.sound_events = bpy.props.StringProperty()
    bpy.types.Object.script_events = bpy.props.StringProperty()
    bpy.types.Object.reaction_events = bpy.props.StringProperty()
    bpy.types.Object.play_effect_events = bpy.props.StringProperty()
    bpy.types.Object.stop_effect_events = bpy.props.StringProperty()
    bpy.types.Object.disable_lipsync_events = bpy.props.StringProperty()

    bpy.types.Object.explicit_namespaces = bpy.props.StringProperty()
    bpy.types.Object.reference_namespace_hash = bpy.props.StringProperty()
    bpy.types.Object.initial_offset_q = bpy.props.StringProperty()
    bpy.types.Object.initial_offset_t = bpy.props.StringProperty()
    bpy.types.Object.snap_events = bpy.props.StringProperty()
    bpy.types.Object.additional_snap_frames = bpy.props.StringProperty()
    bpy.types.Object.visibility_events = bpy.props.StringProperty()
    bpy.types.Object.world_rig = bpy.props.StringProperty()
    bpy.types.Object.world_bone = bpy.props.StringProperty()
    bpy.types.Object.use_world_bone_as_root = bpy.props.BoolProperty(default=False)

    bpy.types.Object.relative_rig = bpy.props.StringProperty()
    bpy.types.Object.relative_bone = bpy.props.StringProperty()
    bpy.types.Object.use_full_precision = bpy.props.BoolProperty(default=False)

    # OLD STUFF
    bpy.types.Scene.rig_name = bpy.props.StringProperty()
    bpy.types.Scene.reset_initial_offset_t = bpy.props.StringProperty()
    bpy.types.Scene.parent_events = bpy.props.StringProperty()
    bpy.types.Scene.sound_events = bpy.props.StringProperty()
    bpy.types.Scene.explicit_namespaces = bpy.props.StringProperty()
    bpy.types.Scene.reference_namespace_hash = bpy.props.StringProperty()
    bpy.types.Scene.initial_offset_q = bpy.props.StringProperty()
    bpy.types.Scene.initial_offset_t = bpy.props.StringProperty()
    bpy.types.Scene.snap_events = bpy.props.StringProperty()
    bpy.types.Scene.additional_snap_frames = bpy.props.StringProperty()
    bpy.types.Scene.visibility_events = bpy.props.StringProperty()
    bpy.types.Scene.world_rig = bpy.props.StringProperty()
    bpy.types.Scene.world_bone = bpy.props.StringProperty()

    # bpy.types.Object.script_idx = IntProperty(name="Index for my_list", default=0)
    # bpy.types.Object.sound_idx = IntProperty(name="Index for sound_idx", default=0)
    bpy.types.Object.actor_idx = IntProperty(name="Index for actors", default=0)
    bpy.types.Object.state_idx = IntProperty(name="Index for state", default=0)
    bpy.types.Object.controller_idx = IntProperty(name="Index for state", default=0)
    bpy.types.Object.posture_idx = IntProperty(name="Index for state", default=0)
    bpy.types.Object.state_connection_idx = IntProperty(name="Index for state", default=0)

    #  bpy.types.Object.clip_idx = IntProperty(name="Index for clip", default=0)
    bpy.types.Scene.is_overlay = bpy.props.BoolProperty(default=False)

    bpy.types.Scene.watcher_running = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.clip_name = bpy.props.StringProperty()
    bpy.types.Scene.clip_name_prefix = bpy.props.StringProperty()
    bpy.types.Scene.clip_splits = bpy.props.StringProperty()


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

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
    del bpy.types.Object.world_rig
    del bpy.types.Object.world_bone
    del bpy.types.Object.reaction_events
    del bpy.types.Object.visibility_events
    del bpy.types.Object.play_effect_events
    del bpy.types.Object.stop_effect_events
    del bpy.types.Object.disable_lipsync_events
    # OLD STUFF
    del bpy.types.Scene.rig_name
    del bpy.types.Scene.reset_initial_offset_t
    del bpy.types.Scene.parent_events
    del bpy.types.Scene.sound_events
    del bpy.types.Scene.explicit_namespaces
    del bpy.types.Scene.reference_namespace_hash
    del bpy.types.Scene.initial_offset_q
    del bpy.types.Scene.initial_offset_t
    del bpy.types.Scene.snap_events
    del bpy.types.Scene.additional_snap_frames
    del bpy.types.Scene.visibility_events
    del bpy.types.Scene.world_rig
    del bpy.types.Scene.world_bone

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
