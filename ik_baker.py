import math
import bpy
from functools import lru_cache
from collections import defaultdict
import time

START_IDX = 0
END_IDX = 1

def get_ik_targets(obj):
    for ik_target in obj.ik_targets:
        if ik_target.target_bone == "b__ROOT__":
            yield ik_target

    for ik_target in obj.ik_targets:
        if ik_target.target_bone != "b__ROOT__":
            yield ik_target

class s4animtool_OT_bakeik(bpy.types.Operator):
    """Bake the IK weights"""
    bl_idname = "s4animtools.bakeik"
    bl_label = "Bake ik"
    bl_options = {"REGISTER", "UNDO"}

    def get_keyframes(self, obj, data_path):
        keyframes = []
        anim = obj.animation_data
        if anim is not None and anim.action is not None:
            for fcu in anim.action.fcurves:
                if fcu.data_path == data_path:
                    for keyframe in fcu.keyframe_points:
                        x, y = keyframe.co
                        if x not in keyframes:
                            keyframes.append((math.ceil(x)))
        return keyframes

    def set_interpolation_keyframes(self, obj, bone):
        """
            IK Ranges are always a set of two keyframes, start and end.
            What this does is find the previous and next ik weights, and set the ik
            weight to be zero on those for a smooth blend.
        """
        frames = {}

        for weight_idx in range(11):
            keyframes = self.get_keyframes(obj, f'pose.bones["{bone.name}"].ik_weight_{weight_idx}')
            if len(keyframes) % 2 != 0 and len(keyframes) != 1:
                raise Exception(f"IK Ranges on ik weights aren't even or a single frame... somehow. {len(keyframes)}")
            else:
                if len(keyframes) == 1:
                    continue
                if len(keyframes) == 0:
                    continue
                for i in range(0, len(keyframes), 2):
                    frames[(bone.name, weight_idx, math.floor(i/2))] = (keyframes[i], keyframes[i+1])
                #print(len(frames[(bone.name,weight_idx)]))
        frames_ordered = sorted(frames,key=lambda k: frames[k][0])
        #TODO what is this pls rewrite

        for idx, item in enumerate(frames_ordered):
            bone, weight_idx, range_idx = item
            if idx == 0:
                pre_start_frame = -1
            else:
                pre_start_frame = frames[frames_ordered[idx - 1]][END_IDX]
            # TODO ugly hack
            if pre_start_frame == 0:
                pre_start_frame = -1
            """
            Set post end frame to beyond the end of a clip if the frame
            it's requesting is beyond the current clip range. +1 offset too for some reason

            """
            if idx + 1 >= len(frames_ordered):
                post_end_frame = frames[frames_ordered[idx]][END_IDX] + 1
            else:
                """
                Get the next ik target and set the weight to be zero on this ik target weight.
                """
                next_ik_target_range = frames_ordered[idx + 1]
                post_end_frame = frames[next_ik_target_range][START_IDX]
            data_path = f'pose.bones["{bone}"].ik_weight_{weight_idx}'
            fc = obj.animation_data.action.fcurves.find(data_path)
            fc.keyframe_points.insert(pre_start_frame, 0)
            fc.keyframe_points.insert(post_end_frame, 0)
            fc.update()
    def execute(self, context):
        t1 = time.time()
        obj = context.object
        bones_to_interpolate = []
        positions = defaultdict(list)
        quaternions = defaultdict(list)
        if obj.ik_idx >= 0 and obj.ik_targets:
            s4animtool_OT_bakeik.remove_IK(obj)
            for idx, item in enumerate(get_ik_targets(obj)):
                chain_bone = obj.pose.bones[item.chain_bone]
                chain_idx = item.chain_idx
                target_rig = bpy.data.objects[item.target_obj]
                target_bone = target_rig.pose.bones[item.target_bone]
                quaternions[(chain_bone, target_bone, target_rig)] = defaultdict(list)
                positions[(chain_bone, target_bone, target_rig)] = defaultdict(list)

        if obj.ik_idx >= 0 and obj.ik_targets:
            for i in range(context.scene.frame_start, context.scene.frame_end, 1):
                bpy.context.scene.frame_set(i)

                for idx, item in enumerate(get_ik_targets(obj)):
                    chain_bone, target_bone, target_rig = self.get_bonedata(item, obj)

                    src_matrix = target_rig.matrix_world @ target_bone.matrix
                    target_matrix = obj.matrix_world @ chain_bone.matrix
                    matrix_data = src_matrix.inverted() @ target_matrix
                    rotation_data = matrix_data.to_quaternion()
                    translation_data = matrix_data.to_translation()
                    for axis_idx, value in enumerate(translation_data):
                        positions[(chain_bone, target_bone, target_rig)][axis_idx].extend([i, value])
                    for axis_idx, value in enumerate(rotation_data):
                        quaternions[(chain_bone, target_bone, target_rig)][axis_idx].extend([i, value])


            for potential_ik_bone in obj.pose.bones:
                for idx in range(11):
                    for pos_idx in range(3):
                        data_path = f'pose.bones["{potential_ik_bone.name}"].ik_pos_{idx}'
                        old_fc = obj.animation_data.action.fcurves.find(data_path, index=pos_idx)
                        if old_fc is not None:
                            obj.animation_data.action.fcurves.remove(old_fc)

                    for rot_idx in range(4):
                        data_path = f'pose.bones["{potential_ik_bone.name}"].ik_rot_{idx}'
                        old_fc = obj.animation_data.action.fcurves.find(data_path, index=rot_idx)
                        if old_fc is not None:
                            obj.animation_data.action.fcurves.remove(old_fc)
                    data_path = f'pose.bones["{potential_ik_bone.name}"].ik_weight_{idx}'
                    old_fc = obj.animation_data.action.fcurves.find(data_path)
                    if old_fc is not None:
                        obj.animation_data.action.fcurves.remove(old_fc)
            current_bone_idx = defaultdict(int)

            for idx, item in enumerate(get_ik_targets(obj)):

                chain_bone, target_bone, target_rig = self.get_bonedata(item, obj)

                for pos_idx in range(3):
                    data_path = f'pose.bones["{chain_bone.name}"].ik_pos_{current_bone_idx[chain_bone]}'

                    fc = obj.animation_data.action.fcurves.new(data_path, index=pos_idx)
                    #print(positions[(chain_bone, target_bone, target_rig)][pos_idx])
                    fc.keyframe_points.add(round(len(positions[(chain_bone, target_bone, target_rig)][pos_idx]) / 2))
                    fc.keyframe_points.foreach_set("co", positions[(chain_bone, target_bone, target_rig)][pos_idx])
                    fc.update()
                for rot_idx in range(4):
                    data_path = f'pose.bones["{chain_bone.name}"].ik_rot_{current_bone_idx[chain_bone]}'

                    fc = obj.animation_data.action.fcurves.new(data_path, index=rot_idx)

                    fc.keyframe_points.add(round(len(quaternions[(chain_bone, target_bone, target_rig)][rot_idx]) / 2))
                    fc.keyframe_points.foreach_set("co", quaternions[(chain_bone, target_bone, target_rig)][rot_idx])
                    fc.update()
                current_bone_idx[chain_bone] += 1
        current_bone_idx = defaultdict(int)

        if obj.ik_idx >= 0 and obj.ik_targets:
            for idx, item in enumerate(get_ik_targets(obj)):
                chain_bone = obj.pose.bones[item.chain_bone]
                chain_idx = item.chain_idx

                target_rig = bpy.data.objects[item.target_obj]

                data_path = f'pose.bones["{chain_bone.name}"].ik_weight_{current_bone_idx[chain_bone]}'
                old_fc = obj.animation_data.action.fcurves.find(data_path)
                if old_fc is not None:
                    obj.animation_data.action.fcurves.remove(old_fc)
                fc = obj.animation_data.action.fcurves.new(data_path)



                for range_value in item.ranges:
                    if range_value.start_time == range_value.end_time:
                        if range_value.start_time == 0:
                            fc.keyframe_points.insert(-1, 0)
                            fc.keyframe_points.insert(0, 0)

                    else:
                        fc.keyframe_points.insert(range_value.start_time, 1)
                        fc.keyframe_points.insert(range_value.end_time, 1)
                fc.update()
                if chain_bone not in bones_to_interpolate:
                    bones_to_interpolate.append(chain_bone)
                current_bone_idx[chain_bone] += 1

        for bone in bones_to_interpolate:
            self.set_interpolation_keyframes(obj, bone)
        bpy.context.view_layer.objects.active = obj
        t2 = time.time()

        print(f"Took {t2-t1} seconds for ik baking")
        return {'FINISHED'}

    def create_ik_target_name(self, chain_bone, obj, target_bone, target_rig, chain_idx):
        ik_target_empty_name = "{} IK {} {} {} {}".format(obj.name.strip(), chain_idx, chain_bone.name,
                                                       target_rig.name, target_bone.name)
        return ik_target_empty_name

    def get_bonedata(self, item, obj):
        chain_bone = obj.pose.bones[item.chain_bone]
        target_rig = bpy.data.objects[item.target_obj]
        target_bone = target_rig.pose.bones[item.target_bone]
        return chain_bone, target_bone, target_rig

    @staticmethod
    def remove_IK(obj):
        for scn_obj in bpy.data.objects:
            split = scn_obj.name.split(" ")
            if len(split) >= 2:
                if split[0] == obj.name.strip() and split[1] == "IK":
                    bpy.data.objects.remove(scn_obj, do_unlink=True)
        for bone in obj.pose.bones:
            for constraint in bone.constraints[:]:
                if constraint.type == "COPY_TRANSFORMS":
                    if constraint.name.startswith("IKFollow"):
                        bone.constraints.remove(constraint)
        bpy.context.view_layer.update()
        for fcu in obj.animation_data.action.fcurves[:]:
            for bone in obj.pose.bones:
                try:

                    if fcu.data_path.startswith('pose.bones["{}"].constraints["{}'.format(bone.name, "IKFollow")):
                        obj.animation_data.action.fcurves.remove(fcu)
                except:
                    pass