from _s4animtools.rig_constants import cas, slot
import _s4animtools
import math

class AnimationChannelDataBase:
    def __init__(self, name):
        self.name = name
        self.values = {}

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
        indices = self.get_animated_frame_indices()
        if len(indices) > 0:
            return indices[-1]
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
        return not self.are_two_keyframes_same(new_keyframe, animation_data)

    @staticmethod
    def are_two_keyframes_same(frame_a, frame_b):
        """
        Compares two keyframes to check if they are the same.
        """
        raise Exception("You need to implement this.")

    @property
    def frame_count(self):
        return len(self.values)

class AnimationDataTranslation(AnimationChannelDataBase):
    @staticmethod
    def are_two_keyframes_same(frame_a, frame_b):
        """
        Compares two keyframes to check if they are the same.
        """
        return AnimationDataTranslation.get_distance(frame_a, frame_b) < 0.001

    # TODO Move this somewhere else
    @staticmethod
    def get_distance(posA, posB):
        distance = math.sqrt((posA.x - posB.x) ** 2 + (posA.y - posB.y) ** 2 + (posA.z - posB.z) ** 2)
        # print(distance)
        return distance


class AnimationDataRotation(AnimationChannelDataBase):
    @staticmethod
    def are_two_keyframes_same(frame_a, frame_b):
        """
        Compares two keyframes to check if they are the same.
        """
        return (frame_a - frame_b).magnitude < 0.001


class AnimationBoneData:
    def __init__(self, animation_exporter):
        self.channels = []
        self.animation_exporter = animation_exporter
        self.create_animation_channels()

    def create_animation_channels(self):
        self.channels.append(AnimationDataTranslation("Translation"))
        self.channels.append(AnimationDataTranslation("Rotation"))

    def get_channel_matching_name(self, name):
        for channel in self.channels:
            if channel.name == name:
                return channel

    def get_translation_channel(self):
        return self.get_channel_matching_name("Translation")

    def get_rotation_channel(self):
        return self.get_channel_matching_name("Rotation")

    def get_matrix_data(self, bone, parent_bone):
        src_matrix = self.animation_exporter.source_rig.matrix_world @ bone.matrix
        dst_matrix = self.animation_exporter.target_rig.matrix_world @ parent_bone.matrix
        matrix_data = dst_matrix.inverted() @ src_matrix
        rotation_data = matrix_data.to_quaternion()
        translation_data = matrix_data.to_translation()
        return translation_data, rotation_data

    def serialize_animation_data(self, bone, parent_bone, frame_idx):
        translation_data, rotation_data = self.get_matrix_data(bone, parent_bone)
        self.get_translation_channel().add_keyframe(translation_data.copy(), frame_idx)
        self.get_rotation_channel().add_keyframe(rotation_data.copy(), frame_idx)

    def force_serialize_animation_data(self, bone, parent_bone, frame_idx):
        translation_data, rotation_data = self.get_matrix_data(bone, parent_bone)
        self.get_translation_channel().add_keyframe(translation_data.copy(), frame_idx, force=True)
        self.get_rotation_channel().add_keyframe(rotation_data.copy(), frame_idx, force=True)
    def __str__(self):
        str = ""
        str += f"Channels: \n"
        for channel in self.channels:
            str += f"{channel.name}  - {channel.frame_count}\n"
        return str
class AnimationExporter:
    def __init__(self, source_rig, target_rig):
        self.animated_frame_data = {}
        self.source_rig = source_rig
        self.target_rig = target_rig
        self.root_bone = self.source_rig.pose.bones["b__ROOT__"]
        self.exported_channels = []
    @property
    def animated_bones(self):
        return self.animated_frame_data.keys()

    def create_animation_data(self):
        for bone in self.source_rig.pose.bones:
            if slot in bone.name:
                continue
            self.animated_frame_data[bone.name] = AnimationBoneData(self)

    def animate_recursively(self, idx, force=False):
        self.animate_frame(self.root_bone, idx, force)

    def animate_frame(self, bone, idx, force):

        parent_bone = bone.parent
        if parent_bone is None:
            parent_bone = bone
        if force:
            self.animated_frame_data[bone.name].force_serialize_animation_data(bone, parent_bone, idx)
        else:
            self.animated_frame_data[bone.name].serialize_animation_data(bone, parent_bone, idx)

        for child in bone.children:
            if slot in child.name:
                continue
            self.animate_frame(child, idx, force)

    def export_to_channels(self):
        self.export_single_bone_to_channel(self.root_bone)
        return self.exported_channels

    def export_single_bone_to_channel(self, bone):
        """
        Exports animation data and adds it to the exported channels li st.
        :param bone:
        :return: none
        """
        animation_data = self.animated_frame_data[bone.name]

        location_channel = _s4animtools.channels.translation_channel.TranslationChannel(bone.name, 18, 1)
        location_channel.setup(animation_data.get_translation_channel())
        self.exported_channels.append(location_channel)

        rotation_channel = _s4animtools.channel.Channel(bone.name, 20, 2)
        rotation_channel.setup(animation_data.get_rotation_channel())
        self.exported_channels.append(rotation_channel)

        for child in bone.children:
            if slot in child.name:
                continue
            self.export_single_bone_to_channel(child)

    def __str__(self):
        str = ""
        for bone in self.animated_frame_data:
            str += f"{bone} - {self.animated_frame_data[bone]}"
        return str
