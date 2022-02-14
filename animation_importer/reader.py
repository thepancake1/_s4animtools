import traceback
from _s4animtools.animation_importer.structure.header import Header
from _s4animtools.animation_importer.structure.clip import S4Clip
from _s4animtools.animation_importer.types.event_list import ClipEvent
import bpy, bmesh
import csv
import glob
import os
from collections import defaultdict
from mathutils import Vector, Matrix, Quaternion

name_to_event_type = {"SOUNDS": "sound_events_list", "PARENT": "parent_events_list",
                      "VISIBILITY": "visibility_events_list",
                      "SCRIPT": "script_events_list", "VFX": "play_effect_events_list",
                      "STOP EFFECT": "stop_effect_events_list",
                      "SUPPRESS LIPSYNC": "disable_lipsync_events_list"}

class AnimationImporter:


    def __init__(self, filepath):
        self.filepath = filepath
        self.scene = bpy.context.scene
        self.rig_name = "x"
        self.rig_obj = bpy.data.objects[self.rig_name]
        self.root_bone = bpy.data.objects[self.rig_name].pose.bones["b__ROOT__"]
        self.all_channel_data_string = defaultdict(str)
        self.all_clips_event_strings = defaultdict(str)
        self.all_clip_names = []
        self.current_frame = 0
        self.highest_frame = 0
        self.last_clip_frame_count = 0
        self.clip_splits = {}
        self.clip_timeshifts = {}
        self.frame_data = {}
        self.bone_animation_data = defaultdict(defaultdict)
    def read_clip_file(self, file):
        try:
            with open(file, "rb") as clip_file:
                header, clip_name, events = Header().deserialize(clip_file)
                clip, channels = S4Clip().deserialize(clip_file, file.split("/")[-1])
                self.all_channel_data_string = defaultdict(str)
                self.all_clips_event_strings = defaultdict(str)
                for channel in channels:
                    bone_data = channel.dump(clip_name)
                    for channel_data in bone_data.keys():
                        self.all_channel_data_string[channel_data] = bone_data[channel_data]
                events_string = ClipEvent().dump(events)
                self.all_clips_event_strings[clip_name] = events_string
                self.all_clip_names.append(clip_name)
                self.read_animation_event_data(round(self.highest_frame/30,6)
        except Exception as e:
            print(e)

        for channel in [channel for channel in all_channel_data_string.keys() if channel.startswith(clip_name) in channel]:
            pass
    def animate_one_clip(self, file, clip_name):
        for list_name in name_to_event_type.values():
            getattr(self.rig_obj, list_name).clear()

        all_channel_data_string, events_string = self.read_clip_file(file)
        self.events_string = events_string
        self.read_animation_event_data(round(self.highest_frame / 30, 6))
        for clip_name in self.all_clip_names:
            for channel in [channel for channel in all_channel_data_string.keys() if channel.startswith(clip_name) in channel]:
                bone_name = channel(os.sep)[-1].split("-")[0]
                channel_name = channel.split("_")[-1].split(".")[0]
                if bone_name in bone_animation_data:
                    if "SubChannelType.Orientation" in channel:
                        frame_data = self.bone_animation_data[bone_name]["Orientation"]

                    elif "SubChannelType.Translation" in channel:
                        frame_data = bone_animation_data[bone_name]["Translation"]

                    elif "SubChannelType.Scale" in channel:
                        print(bone_animation_data[bone_name])
                        frame_data = bone_animation_data[bone_name]["Scale"]
                    else:
                        continue

                    with open(file, "r") as csv_file:
                        csv_reader = csv.reader(csv_file, delimiter=',')
                        line_count = 0
                        for row in csv_reader:
                            try:
                                new_clip_count = last_clip_frame_count + int(row[0])
                                frame_data[new_clip_count] = list(map(float, row[1:]))
                                if new_clip_count > highest_frame:
                                    highest_frame = new_clip_count
                            except Exception as e:
                                break

                self.clip_splits[clip_name] = highest_frame
                self.last_clip_frame_count = highest_frame
    def read_animation_event_data(self, current_timeshift):
        current_element = ""
        current_line = 0
        lines = self.events_string
        while current_line < len(lines):
            line = lines[current_line].strip()
            args = line.split(",")

            if line.startswith("==="):
                current_element = line[3:-3]
                current_line += 1
            else:
                event_str = f"{round(float(args[0]) + current_timeshift, 6)}" + "," + ",".join(args[1:])
                if current_element in name_to_event_type:
                    attribute_name = name_to_event_type[current_element]
                    getattr(self.rig_obj, attribute_name).add()
                    getattr(self.rig_obj, attribute_name)[-1].info = event_str
                current_line += 1

    def reset_bones_to_rest(self):
        original_matrices = {}
        original_normal_matrices = {}
        bone_animation_data = defaultdict(defaultdict)

        for pose_bone in rig_obj.pose.bones:
            if pose_bone.bone.parent is None:
                original_matrices[pose_bone.name] = Matrix(pose_bone.bone.matrix_local.to_3x3())
            else:
                original_matrices[pose_bone.name] = Matrix(
                    (pose_bone.bone.matrix_local @ pose_bone.bone.parent.matrix_local).to_3x3())
            original_matrices[pose_bone.name].resize_4x4()
            original_normal_matrices[pose_bone.name] = pose_bone.bone.matrix_local.to_3x3()
            original_normal_matrices[pose_bone.name].resize_4x4()
            bone_animation_data[pose_bone.name] = {"Translation": {}, "Orientation": {}, "Scale": {}}














def animate_one_frame(current_clip_frame, bone):
    bone_name = bone.name
    current_matrix = bone.bone.matrix_local
    rotation_matrix = current_matrix.to_3x3().to_4x4()
    translation_matrix = Matrix.Translation(current_matrix.to_translation())

    scale_matrix_x1 = Matrix.Scale(current_matrix.to_scale()[0], 4, (1.0, 0.0, 0.0))
    scale_matrix_y1 = Matrix.Scale(current_matrix.to_scale()[1], 4, (0.0, 1.0, 0.0))
    scale_matrix_z1 = Matrix.Scale(current_matrix.to_scale()[2], 4, (0.0, 0.0, 1.0))
    scale_matrix = scale_matrix_x1 @ scale_matrix_y1 @ scale_matrix_z1

    frame_data = bone_animation_data[bone_name]

    rotation_data = False
    translation_data = False
    scale_data = False
    if "Orientation" in frame_data:
        rotation_data = current_clip_frame in frame_data["Orientation"].keys()
    if "Translation" in frame_data:
        translation_data = current_clip_frame in frame_data["Translation"].keys()
    if "Scale" in frame_data:
        scale_data = current_clip_frame in frame_data["Scale"].keys()
    if translation_data or rotation_data or scale_data:
        if rotation_data:
            fd = frame_data["Orientation"][current_clip_frame]
            rotation_matrix = Quaternion((fd[3], fd[0], fd[1], fd[2])).to_matrix().to_4x4()

        if translation_data:
            fd = frame_data["Translation"][current_clip_frame]
            translation_matrix = Matrix.Translation((fd[0], fd[1], fd[2])).to_4x4()

        if scale_data:
            fd = frame_data["Scale"][current_clip_frame]

            scale_matrix_x2 = Matrix.Scale(fd[0], 4, (1.0, 0.0, 0.0))
            scale_matrix_y2 = Matrix.Scale(fd[1], 4, (0.0, 1.0, 0.0))
            scale_matrix_z2 = Matrix.Scale(fd[2], 4, (0.0, 0.0, 1.0))
            scale_matrix = (scale_matrix_x2 @ scale_matrix_y2 @ scale_matrix_z2).to_4x4()

        if bone.parent:
            transform_matrix = bone.parent.matrix @ translation_matrix @ rotation_matrix @ scale_matrix
            bone.matrix = transform_matrix

        if scale_data:
            bone.keyframe_insert(data_path='scale', frame=current_clip_frame)

        if rotation_data:
            bone.keyframe_insert(data_path='rotation_quaternion', frame=current_clip_frame)
        if translation_data:
            bone.keyframe_insert(data_path='location', frame=current_clip_frame)
    for child in bone.children:
        animate_one_frame(current_clip_frame, child)


def recursive_bone_animate(bone):

    ob = bone
    bone_name = bone.name

    if bone_name in bone_animation_data:
        current_matrix = bone.bone.matrix_local
        rotation_matrix = current_matrix.to_3x3().to_4x4()
        translation_matrix = Matrix.Translation(current_matrix.to_translation())

        scale_matrix_x1 = Matrix.Scale(current_matrix.to_scale()[0], 4, (1.0, 0.0, 0.0))
        scale_matrix_y1 = Matrix.Scale(current_matrix.to_scale()[1], 4, (0.0, 1.0, 0.0))
        scale_matrix_z1 = Matrix.Scale(current_matrix.to_scale()[2], 4, (0.0, 0.0, 1.0))
        scale_matrix = scale_matrix_x1 @ scale_matrix_y1 @ scale_matrix_z1

        frame_data = bone_animation_data[bone_name]
        #TODO imporove the perofrmance of this! Currently it plays back the animation in the viewport for each bone. which is very very slow.
        for current_clip_frame in range(0, last_clip_frame_count):
            bpy.context.scene.frame_set(current_clip_frame)
            bpy.context.view_layer.update()

            rotation_data = False
            translation_data = False
            scale_data = False
            if "Orientation" in frame_data:
                rotation_data = current_clip_frame in frame_data["Orientation"].keys()
            if "Translation" in frame_data:
                translation_data = current_clip_frame in frame_data["Translation"].keys()
            if "Scale" in frame_data:
                scale_data = current_clip_frame in frame_data["Scale"].keys()
            if translation_data or rotation_data or scale_data:
                # format is stored as XYZW
                if rotation_data:
                    fd = frame_data["Orientation"][current_clip_frame]
                    rotation_matrix = Quaternion((fd[3], fd[0], fd[1], fd[2])).to_matrix().to_4x4()

                if translation_data:
                    fd = frame_data["Translation"][current_clip_frame]
                    translation_matrix = Matrix.Translation((fd[0], fd[1], fd[2])).to_4x4()
                if bone_name == "b__ROOT_bind__" and translation_data:
                    print(current_clip_frame, translation_matrix.to_translation())
                if scale_data:
                    fd = frame_data["Scale"][current_clip_frame]

                    scale_matrix_x2 = Matrix.Scale(fd[0], 4, (1.0, 0.0, 0.0))
                    scale_matrix_y2 = Matrix.Scale(fd[1], 4, (0.0, 1.0, 0.0))
                    scale_matrix_z2 = Matrix.Scale(fd[2], 4, (0.0, 0.0, 1.0))
                    scale_matrix = (scale_matrix_x2 @ scale_matrix_y2 @ scale_matrix_z2).to_4x4()

                if bone.parent:
                    transform_matrix = bone.parent.matrix @ scale_matrix @ translation_matrix @ rotation_matrix
                    bone.matrix = transform_matrix

                if scale_data:
                    ob.keyframe_insert(data_path='scale', frame=current_clip_frame)

                if rotation_data:
                    ob.keyframe_insert(data_path='rotation_quaternion', frame=current_clip_frame)
                if translation_data:
                    ob.keyframe_insert(data_path='location', frame=current_clip_frame)
        bone.matrix = current_matrix
    for child in bone.children:
        recursive_bone_animate(child)


scene.clip_splits = ",".join(list(map(str, clip_splits.values())))
scene.clip_name = ",".join(clip_splits.keys())
for current_clip_frame in range(0, last_clip_frame_count):
    bpy.context.scene.frame_set(current_clip_frame)
    bpy.context.view_layer.update()
    animate_one_frame(current_clip_frame, root_bone)

if __name__ == "__main__":
    files = []
    idx = 0



