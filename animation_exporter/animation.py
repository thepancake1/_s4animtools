from _s4animtools.rig_constants import slot
from _s4animtools.channels.translation_channel import Vector3Channel
from _s4animtools.channels.quaternion_channel import QuaternionChannel
from _s4animtools.channels.palette_channel import PaletteTranslationChannel
from _s4animtools.frames.frame import PaletteTranslationFrame, PaletteFrame
from _s4animtools.clip_processing.f1_palette import F1Palette
from collections import defaultdict
from mathutils import Vector, Quaternion
from _s4animtools.channels.palette_channel import PaletteQuaternionChannel, PaletteTranslationChannel
import math

F3 = 3
F4 = 4
IK_TARGET_COUNT = 11

IK_TRANSLATION_SUBTARGET_IDX = 25
IK_ROTATION_SUBTARGET_IDX = 26

TRANSLATION_SUBTARGET_IDX = 1
ROTATION_SUBTARGET_IDX = 2
SCALE_SUBTARGET_IDX = 3

F3_HIGH_PRECISION_NORMALIZED_IDX = 18
F4_SUPER_HIGH_PRECISION_IDX = 20

IK_POLE_TO_BASE = {"b__L_ArmExportPole__" : "b__L_Forearm__",
                   "b__R_ArmExportPole__" : "b__R_Forearm__",
                   "b__L_LegExportPole__" : "b__L_Calf__",
                   "b__R_LegExportPole__" : "b__R_Calf__"}
IK_POLE_TO_PARENT = {"b__L_LegExportPole__" : "b__L_Thigh__",
                    "b__R_LegExportPole__" : "b__R_Thigh__"}

class AnimationChannelDataBase:
    def __init__(self, name):
        self.name = name
        self.values = {}

    def keys(self):
        return self.values.keys()

    def items(self):
        return self.values.items()

    def get_animated_frame_indices(self):
        """
        Returns a list of ints of frames that have animation data.
        """
        return sorted(list(self.values.keys()))

    def get_latest_frame(self):
        """
        Returns greatest animation frame.
        """
        if len(self.values) > 0:
            return max(self.values.keys())
        return -1

    def get_latest_animation_data(self):
        """
        Returns the value of the newest animation frame.
        """
        latest_frame = self.get_latest_frame()
        if latest_frame == -1:
            return None
        else:
            return self.values[latest_frame]

    def add_keyframe(self, new_keyframe, frame_idx, force=False):
        """
        Adds a keyframe if the keyframe is valid.
        """
        if self.validate_keyframe(new_keyframe) or force:
            self.values[frame_idx] = new_keyframe

    def validate_keyframe(self, new_keyframe):
        """
         Validate keyframes. Currently only frame similarity is checked.
         """
        animation_data = self.get_latest_animation_data()
        if animation_data is None:
            return True
        is_identical = self.identical(new_keyframe, animation_data)
        return not is_identical

    @staticmethod
    def identical(frame_a, frame_b):
        """
        Compares two keyframes to check if they are the same.
        """
        raise Exception("You need to implement this.")

    @property
    def frame_count(self):
        return len(self.values)


class AnimationDataMagnitude(AnimationChannelDataBase):
    @staticmethod
    def identical(frame_a, frame_b):
        """
        Compares two keyframes to check if they are the same.
        """
        return (frame_a - frame_b).magnitude < 0.00001


class AnimationBoneData:
    def __init__(self, animation_exporter):
        self.channels = []
        self.animation_exporter = animation_exporter
        self.create_animation_channels()

    def create_animation_channels(self):
        """
        Create AnimationData channels for Translation, Rotation, Scale,
        along with Translation and Rotation IK channels.
        """
        self.channels.append(AnimationDataMagnitude("Translation"))
        self.channels.append(AnimationDataMagnitude("Rotation"))
        self.channels.append(AnimationDataMagnitude("Scale"))

        for i in range(IK_TARGET_COUNT):
            self.channels.append(AnimationDataMagnitude(f"Translation IK {i}"))
            self.channels.append(AnimationDataMagnitude(f"Rotation IK {i}"))

    def get_channel_matching_name(self, name):
        """
        Return the first channel matching the name specified.
        Does not support multiple channels with the same name.
        """
        for channel in self.channels:
            if channel.name == name:
                return channel

    def get_translation_channel(self, ik_idx=-1):
        """
        Returns the translation channel for an ik_idx.
        If ik_idx is -1, then it returns the base translation
        channel data.
        """
        if ik_idx == -1:
            return self.get_channel_matching_name("Translation")
        return self.get_channel_matching_name(f"Translation IK {ik_idx}")

    def get_rotation_channel(self, ik_idx=-1):
        """
        Returns the rotation channel for an ik_idx.
        If ik_idx is -1, then it returns the base rotation
        channel data.
        """
        if ik_idx == -1:
            return self.get_channel_matching_name("Rotation")
        return self.get_channel_matching_name(f"Rotation IK {ik_idx}")

    def get_scale_channel(self):
        """
        Returns the rotation channel for an ik_idx.
        If ik_idx is -1, then it returns the base rotation
        channel data.
        """
        return self.get_channel_matching_name("Scale")

    def get_transform(self, source_rig, source_bone, target_rig, target_bone):
        """
        Returns a tuple of translation, rotation, and scale data of
        the source bone animated to the target bone.
        """

        src_matrix = source_rig.matrix_world @ source_bone.matrix
        dst_matrix = target_rig.matrix_world @ target_bone.matrix
        matrix_data = dst_matrix.inverted() @ src_matrix
        rotation_data = matrix_data.to_quaternion()
        translation_data = matrix_data.to_translation()
        #print(matrix_data.to_scale())
        scale_data = matrix_data.to_scale()

        return translation_data, rotation_data, scale_data

    def get_transform_for_scale(self, source_rig, source_bone, target_rig, target_bone):
        """
        Returns a tuple of translation, rotation, and scale data of
        the source bone animated to the target bone.
        """

        src_matrix = source_rig.matrix_world @ source_bone.matrix
        dst_matrix = target_rig.matrix_world @ target_bone.matrix
        matrix_data = dst_matrix.inverted() @ src_matrix
        scale_data = matrix_data.to_scale()

        scale_matrix_x2 = Matrix.Scale(scale_data[0], 4, (1.0, 0.0, 0.0))
        scale_matrix_y2 = Matrix.Scale(scale_data[1], 4, (0.0, 1.0, 0.0))
        scale_matrix_z2 = Matrix.Scale(scale_data[2], 4, (0.0, 0.0, 1.0))
        scale_data = matrix_data.to_scale()

        return translation_data, rotation_data, scale_data

    def get_transform_and_serialize(self, source_rig, source_bone, target_rig, target_bone, frame_idx, start_frame, ik_idx=-1,
                                    force=False):
        """
        Add keyframe to each of the transform, rotation, and scale channels.
        """
        translation_data, rotation_data, scale_data = self.get_transform(source_rig, source_bone, target_rig, target_bone)
        self.get_translation_channel(ik_idx).add_keyframe(translation_data, frame_idx-start_frame, force)
        self.get_rotation_channel(ik_idx).add_keyframe(rotation_data, frame_idx-start_frame, force)
        self.get_scale_channel().add_keyframe(scale_data, frame_idx-start_frame, force)

    def get_transform_with_offset_and_serialize(self, source_rig, source_bone, bone_to_be_offset, frame_idx, start_frame, ik_idx=-1,
                                                force=False):
        """
        Meant to be used for the export poles.
        The offset should probably be determined automatically, instead of being hardcoded.
        Will not work for pets right now.
        """
        offset = -0.491
        if "Leg" in source_bone.name:
            offset *= -1
        if source_bone.name in IK_POLE_TO_PARENT.keys():
            parent = source_rig.pose.bones[IK_POLE_TO_PARENT[source_bone.name]]
           # print(source_bone.name, parent.name)
        else:
            parent = source_bone.parent
        translation_data = parent.matrix.inverted() @ (bone_to_be_offset.matrix @ Vector((0, offset, 0)))
        self.get_translation_channel(ik_idx).add_keyframe(translation_data, frame_idx-start_frame, force)

    def __str__(self):
        """Returns a string version the animation channels.
        It lists each of the channel names and how many frames are in a single channel.
        """
        str = ""
        str += f"Channels: \n"
        for channel in self.channels:
            str += f"{channel.name}  - {channel.frame_count}\n"
        return str


class AnimationExporter:
    def __init__(self, source_rig, snap_frames, world_rig, world_root, use_full_precision):
        self.animated_frame_data = {}
        self.source_rig = source_rig
        self.snap_frames = snap_frames
        self.root_bone = self.source_rig.pose.bones["b__ROOT__"]
        self.exported_channels = []
        self.world_rig = world_rig
        self.world_root = world_root
        self.use_full_precision = use_full_precision
        self.paletteHolder = F1Palette()
    @property
    def animated_bones(self):
        """
        Returns all the animated bones in an animation.
        Not implemented yet is support for overlays as all potential
        animated bones are listed regardless if they're actually
        animated.
        """
        return self.animated_frame_data.keys()

    def create_animation_data(self):
        """
        Create an AnimationBoneData class for each bone that can be animated.
        """
        for bone in self.source_rig.pose.bones:
            if slot in bone.name:
                continue

            self.animated_frame_data[bone.name] = AnimationBoneData(self)

    def animate_recursively(self, idx, start_frame, force=False):
        """
        Recursively animate all the bones from a rig
        starting from the root bone.
        This assumes that the root bone is called "b__ROOT__"
        """
        self.animate_frame(self.root_bone, idx, start_frame, force)

    def animate_frame(self, source_bone, frame_idx, start_frame, force):
        """
        Animate a bone relative to its parent.
        This function requires the bone, the frame index, the current clip's start frame, and whether a keyframe
        should be inserted without checking if it's identical to previous keyframes.

        If the bone has "slot" in the bone's name, then the bone will not be animated.
        This assumes that slot bones have no children.

        The b__ROOT__ bone is never animated.
        """
        parent_bone = source_bone.parent
        if parent_bone is not None:
            is_parent_root_bone = False
            if source_bone.parent.name == "b__ROOT__":
                is_parent_root_bone = True
                if source_bone.name in IK_POLE_TO_BASE.keys():
                    self.animated_frame_data[source_bone.name].get_transform_with_offset_and_serialize(source_rig =self.source_rig,
                                                                                                       source_bone=source_bone,
                                                                                                       bone_to_be_offset=self.source_rig.pose.bones[IK_POLE_TO_BASE[source_bone.name]],
                                                                                                       frame_idx=frame_idx,
                                                                                                       start_frame=start_frame,
                                                                                                       force=force)
                else:
                    self.animate_bone_relative_to_other_bone(source_bone=source_bone,
                                                             target_rig=self.world_rig,
                                                             target_bone=self.world_root, frame_idx=frame_idx,
                                                             start_frame=start_frame,
                                                             force=force)
            if not is_parent_root_bone:
                if source_bone.name in IK_POLE_TO_BASE.keys():
                    self.animated_frame_data[source_bone.name].get_transform_with_offset_and_serialize(source_rig =self.source_rig,
                                                                                                       source_bone=source_bone,
                                                                                                       bone_to_be_offset=self.source_rig.pose.bones[IK_POLE_TO_BASE[source_bone.name]],
                                                                                                       frame_idx=frame_idx,
                                                                                                       start_frame=start_frame,
                                                                                                       force=force)
                else:
                    self.animated_frame_data[source_bone.name].get_transform_and_serialize(source_rig=self.source_rig, source_bone=source_bone,
                                                                                           target_rig=self.source_rig,
                                                                                           target_bone=parent_bone, frame_idx=frame_idx,
                                                                                           start_frame=start_frame,
                                                                                           force=force)


        for child in source_bone.children:
            if slot in child.name:
                continue
            self.animate_frame(child, frame_idx, start_frame, force)

    def animate_bone_relative_to_other_bone(self, source_bone, target_rig, target_bone, frame_idx, start_frame, ik_idx=-1, force=False):
        """
        Animate a bone relative to another bone.

        This does not recursively go through the children unlike animate_frame.

        Requires source_bone which is the bone you want to animate relative to the target rig's target bone.
        The other parameters are the same as animate_frame()
        """
        self.animated_frame_data[source_bone.name].get_transform_and_serialize(source_rig=self.source_rig,
                                                                               source_bone=source_bone,
                                                                               target_rig=target_rig,
                                                                               target_bone=target_bone, frame_idx=frame_idx,
                                                                               start_frame=start_frame,
                                                                               force=force, ik_idx=ik_idx)


    def add_baked_animation_data_to_frame(self, source_bone_name, start_frame, end_frame, ik_idx=-1):
        translation_data_path = f'pose.bones["{source_bone_name}"].ik_pos_{ik_idx}'
        rotation_data_path = f'pose.bones["{source_bone_name}"].ik_rot_{ik_idx}'

        translation_channel_clip = self.animated_frame_data[source_bone_name].get_translation_channel(ik_idx)
        rotation_channel_clip = self.animated_frame_data[source_bone_name].get_rotation_channel(ik_idx)
        translations = defaultdict(dict)
        for t_axis in range(3):
            fc_t = self.source_rig.animation_data.action.fcurves.find(translation_data_path, index=t_axis)
            for keyframe in fc_t.keyframe_points:
                frame = math.floor(keyframe.co[0])
                if start_frame <= frame < end_frame:
                    translations[frame-start_frame][t_axis] = keyframe.co[1]
        for frame in translations:
            translation_channel_clip.add_keyframe(Vector(translations[frame].values()), frame, force=frame==0)
        rotations = defaultdict(dict)
        for r_axis in range(4):
            fc_r = self.source_rig.animation_data.action.fcurves.find(rotation_data_path,index=r_axis)
            for keyframe in fc_r.keyframe_points:
                frame = math.floor(keyframe.co[0])

                if start_frame <= frame < end_frame:
                    rotations[frame-start_frame][r_axis] = keyframe.co[1]
        for frame in rotations:
            rotation_channel_clip.add_keyframe(Quaternion(rotations[frame].values()), frame, force=frame==0)

    def export_to_channels(self):
        """
        Recursively export all bones starting from the root bone, then
        return the exported channels
        """


        self.recursively_export_bone_animation_to_channels(self.root_bone)
        return self.exported_channels

    def recursively_export_bone_animation_to_channels(self, bone):

        """
        Set up the bone animation data for each of the channels.
        It calculates the Translation, Rotation, and Scale channels,
        as long as the IK channels.

        Note that if an IK channel does not have any keyframes,
        it will not be exported.
        """
        if bone.name != "b__ROOT__":
            animation_data = self.animated_frame_data[bone.name]

            if len(animation_data.get_translation_channel().items()) > 0:
                if self.use_full_precision:
                    location_channel = PaletteTranslationChannel(bone.name, F3, TRANSLATION_SUBTARGET_IDX)
                    translation_channel_data, original_values = self.get_f1_palette_for_channel(animation_data.get_translation_channel(), axis_count=3)
                    location_channel.palette_setup(channel_data=translation_channel_data,snap_frames=self.snap_frames, values=original_values)
                else:
                    location_channel = Vector3Channel(bone.name, F3_HIGH_PRECISION_NORMALIZED_IDX,
                                                          TRANSLATION_SUBTARGET_IDX)
                    location_channel.setup(animation_data.get_translation_channel(), snap_frames=self.snap_frames)

                self.exported_channels.append(location_channel)

            if len(animation_data.get_rotation_channel().items()) > 0:
                if self.use_full_precision:
                    rotation_channel_data, original_values = self.get_f1_palette_for_channel(animation_data.get_rotation_channel(), axis_count=4)

                    rotation_channel = PaletteQuaternionChannel(bone.name, F4, ROTATION_SUBTARGET_IDX)
                    rotation_channel.palette_setup(channel_data=rotation_channel_data,snap_frames=self.snap_frames, values=original_values)
                else:
                    rotation_channel = QuaternionChannel(bone.name, F4_SUPER_HIGH_PRECISION_IDX, ROTATION_SUBTARGET_IDX)
                    rotation_channel.setup(animation_data.get_rotation_channel(), snap_frames=self.snap_frames)
                self.exported_channels.append(rotation_channel)

#
            if len(animation_data.get_scale_channel().items()) > 0:
                if self.use_full_precision:
                    scale_channel = PaletteTranslationChannel(bone.name, F3, SCALE_SUBTARGET_IDX)
                    scale_channel_data, original_values = self.get_f1_palette_for_channel(animation_data.get_scale_channel(), axis_count=3)
                    scale_channel.palette_setup(channel_data=scale_channel_data,
                                                      snap_frames=self.snap_frames,
                                                      values=original_values)
                else:
                    scale_channel = Vector3Channel(bone.name, F3_HIGH_PRECISION_NORMALIZED_IDX, SCALE_SUBTARGET_IDX)
                    scale_channel.setup(animation_data.get_scale_channel(), snap_frames=self.snap_frames)
    #
                self.exported_channels.append(scale_channel)

            for ik_target_idx in range(IK_TARGET_COUNT):
                animation_translation_channel = animation_data.get_translation_channel(ik_target_idx)
                animation_rotation_channel = animation_data.get_rotation_channel(ik_target_idx)
                if len(animation_rotation_channel.items()) > 0 and len(animation_translation_channel.items()) > 0:
                    if self.use_full_precision:
                        translation_channel = PaletteTranslationChannel(bone.name, F3, IK_TRANSLATION_SUBTARGET_IDX + (ik_target_idx * 2))
                        translation_channel_data,original_values = self.get_f1_palette_for_channel(animation_translation_channel, axis_count=3)
                        translation_channel.palette_setup(channel_data=translation_channel_data,
                                                          snap_frames=self.snap_frames,
                                                          values=original_values)
                        rotation_channel = PaletteQuaternionChannel(bone.name, F4, IK_ROTATION_SUBTARGET_IDX + ik_target_idx * 2)
                        rotation_channel_data,original_values = self.get_f1_palette_for_channel(animation_rotation_channel, axis_count=4)
                        rotation_channel.palette_setup(channel_data=rotation_channel_data, snap_frames=self.snap_frames,
                                                       values=original_values)
                    else:
                        translation_channel = Vector3Channel(bone.name, F3_HIGH_PRECISION_NORMALIZED_IDX,
                                                                 IK_TRANSLATION_SUBTARGET_IDX + (ik_target_idx * 2))
                        rotation_channel = QuaternionChannel(bone.name, F4_SUPER_HIGH_PRECISION_IDX,
                                                   IK_ROTATION_SUBTARGET_IDX + ik_target_idx * 2)
                        translation_channel.setup(animation_translation_channel, snap_frames=self.snap_frames)
                        rotation_channel.setup(animation_rotation_channel, snap_frames=self.snap_frames)
                    self.exported_channels.append(translation_channel)
                    self.exported_channels.append(rotation_channel)

        for child in bone.children:
            if slot in child.name:
                continue
            self.recursively_export_bone_animation_to_channels(child)

    def get_f1_palette_for_channel(self, channel, axis_count, axis_order=None):
        original_values = defaultdict(list)
        if axis_order is None:
            if axis_count == 3:
                axis_order = (0, 1, 2)
            elif axis_count == 4:
                axis_order = (1, 2, 3, 0)
        frame_indices = defaultdict(list)
        for frame, data in channel.items():
            values = []

            for axis in range(axis_count):
                original_values[frame].append(data[axis_order[axis]])
                index = self.paletteHolder.try_add_palette_to_palette_values(data[axis])
                values.append(index)
            if axis_count == 3:
                frame_indices[frame] = [values[axis_order[0]], values[axis_order[1]], values[axis_order[2]]]
            elif axis_count == 4:
                frame_indices[frame] = [values[axis_order[0]], values[axis_order[1]], values[axis_order[2]], values[axis_order[3]]]
        return frame_indices, original_values
    def __str__(self):
        """
        Return a string representation of the animation.
        """
        str = ""
        for bone in self.animated_frame_data:
            str += f"{bone} - {self.animated_frame_data[bone]}"
        return str
