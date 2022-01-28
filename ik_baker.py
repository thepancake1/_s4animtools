import math
import bpy
from functools import lru_cache
from collections import defaultdict
import time
class s4animtool_OT_bakeik(bpy.types.Operator):
    """Bake the IK weights"""
    bl_idname = "s4animtools.bakeik"
    bl_label = "Bake ik"

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

        frames = {}
        for constraint in bone.constraints[:]:
            if constraint.type == "COPY_TRANSFORMS":
                if constraint.name.startswith("IKFollow"):
                    keyframes = self.get_keyframes(obj, 'pose.bones["{}"].constraints["{}"].influence'.format(bone.name, constraint.name))
                    if len(keyframes) % 2 != 0:
                        raise Exception("Number keyframes on ik weights aren't even... somehow.")
                    for i in range(0, len(keyframes), 2):
                        frames[(constraint, i / 2)] = []

                        frames[(constraint, i / 2)] = (keyframes[i], keyframes[i+1])

            if not constraint.name.startswith("IKFollow"):
                constraint.mute = True

        frames_ordered = sorted(frames,key=lambda k: frames[k][0])
        #print(frames_ordered)
       # print(frames)
        #TODO what is this pls rewrite
        for idx, item in enumerate(frames_ordered):
            constraint, range_idx = item
            if idx == 0:
                pre_start_frame = -1
            else:
                pre_start_frame = frames[frames_ordered[idx - 1]][1]

            if idx + 1 >= len(frames_ordered):
                post_end_frame = frames[frames_ordered[idx]][1] + 1
            else:
                post_end_frame = frames[frames_ordered[idx + 1]][0]
           # print(pre_start_frame, post_end_frame)
            constraint.influence = 0.0
            constraint.keyframe_insert(data_path="influence", frame=pre_start_frame)
            constraint.influence = 0.0
            constraint.keyframe_insert(data_path="influence", frame=post_end_frame)
           # print(bone.name, constraint.name, pre_start_frame, post_end_frame)
    def execute(self, context):
        t1 = time.time()
        obj = context.object
        bones_to_interpolate = []
        positions = defaultdict(list)
        quaternions = defaultdict(list)
        if obj.ik_idx >= 0 and obj.ik_targets:
            s4animtool_OT_bakeik.remove_IK(obj)
            for idx, item in enumerate(obj.ik_targets):
                chain_bone = obj.pose.bones[item.chain_bone]
                chain_idx = item.chain_idx
                target_rig = bpy.data.objects[item.target_obj]
                target_bone = target_rig.pose.bones[item.target_bone]
                if item.holder_src_bone != "":
                    holder_src_bone = obj.pose.bones[item.holder_src_bone]
                else:
                    holder_src_bone = None
                ik_target_empty_name = self.create_ik_target_name(chain_bone, obj, target_bone,
                                                                  target_rig, chain_idx)
                if ik_target_empty_name not in bpy.data.objects:
                    o = bpy.data.objects.new(ik_target_empty_name, None)
                    child_of = o.constraints.new('CHILD_OF')
                    o.empty_display_size = 0.2
                    o.empty_display_type = 'PLAIN_AXES'
                    o.rotation_mode = 'QUATERNION'
                    child_of.target = target_rig
                    child_of.subtarget = target_bone.name
                    bpy.context.scene.collection.objects.link(o)

                else:
                    o = bpy.data.objects[ik_target_empty_name]
                o.animation_data_create()
                o.animation_data.action = bpy.data.actions.new(name=ik_target_empty_name)
                quaternions[(chain_bone, target_bone, target_rig)] = defaultdict(list)
                positions[(chain_bone, target_bone, target_rig)] = defaultdict(list)



                src_bone = holder_src_bone
                if holder_src_bone is None:
                    src_bone = chain_bone

                for constraint in src_bone.constraints:
                    if not constraint.name.startswith("IKFollow"):
                        constraint.mute = False


        if obj.ik_idx >= 0 and obj.ik_targets:

            for i in range(context.scene.frame_start, context.scene.frame_end, 1):
                #print(f"Frame {i}")

                bpy.context.scene.frame_set(i)

                for idx, item in enumerate(obj.ik_targets):
                    chain_bone, o, target_bone, target_rig = self.get_bonedata(item, obj)

                    src_matrix = target_rig.matrix_world @ target_bone.matrix
                    target_matrix = obj.matrix_world @ chain_bone.matrix
                    matrix_data = src_matrix.inverted() @ target_matrix
                    rotation_data = matrix_data.to_quaternion()
                    translation_data = matrix_data.to_translation()
                    for axis_idx, value in enumerate(translation_data):
                        positions[(chain_bone, target_bone, target_rig)][axis_idx].extend([i, value])
                    for axis_idx, value in enumerate(rotation_data):
                        quaternions[(chain_bone, target_bone, target_rig)][axis_idx].extend([i, value])
                    #o.keyframe_insert(data_path="location", frame=i)
                    #o.keyframe_insert(data_path="rotation_quaternion", frame=i)
            for idx, item in enumerate(obj.ik_targets):
                #print("Setting stuff")
                chain_bone, o, target_bone, target_rig = self.get_bonedata(item, obj)
                for pos_idx in range(3):
                    data_path = f'location'
                    fc = o.animation_data.action.fcurves.find(data_path, index=pos_idx)
                    if not fc:
                        fc = o.animation_data.action.fcurves.new(data_path, index=pos_idx)
                    #print(positions[(chain_bone, target_bone, target_rig)][pos_idx])
                    fc.keyframe_points.add(round(len(positions[(chain_bone, target_bone, target_rig)][pos_idx]) / 2))
                    fc.keyframe_points.foreach_set("co", positions[(chain_bone, target_bone, target_rig)][pos_idx])
                    fc.update()

                for pos_idx in range(4):
                    data_path = f'rotation_quaternion'
                    fc = o.animation_data.action.fcurves.find(data_path, index=pos_idx)
                    if not fc:
                        fc = o.animation_data.action.fcurves.new(data_path, index=pos_idx)
                    fc.keyframe_points.add(round(len(quaternions[(chain_bone, target_bone, target_rig)][pos_idx]) / 2))

                    fc.keyframe_points.foreach_set("co", quaternions[(chain_bone, target_bone, target_rig)][pos_idx])
                    fc.update()
        if obj.ik_idx >= 0 and obj.ik_targets:
            for idx, item in enumerate(obj.ik_targets):
                chain_bone = obj.pose.bones[item.chain_bone]
                chain_idx = item.chain_idx

                target_rig = bpy.data.objects[item.target_obj]
                target_bone = target_rig.pose.bones[item.target_bone]
                if item.holder_src_bone != "":
                    holder_src_bone = obj.pose.bones[item.holder_src_bone]
                else:
                    holder_src_bone = None

                src_bone = holder_src_bone
                if holder_src_bone is None:
                    src_bone = chain_bone

                ik_target_empty_name = self.create_ik_target_name(chain_bone, obj, target_bone,
                                                                  target_rig, chain_idx)
                o = bpy.data.objects[ik_target_empty_name]

                bpy.context.view_layer.objects.active = o

                bpy.ops.constraint.childof_clear_inverse(constraint="Child Of", owner='OBJECT')

                for range_value in item.ranges:

                    if range_value.start_time == range_value.end_time:
                        raise Exception("Creating an IKTarget with a duration of 0. This isn't possible.")

                    ik_constraint_name = "IKFollow {} {}".format(target_rig.name, target_bone.name)
                    ik_constraint = src_bone.constraints.get(ik_constraint_name)
                    if ik_constraint is None:
                        ik_constraint = src_bone.constraints.new("COPY_TRANSFORMS")
                        ik_constraint.name = ik_constraint_name
                    ik_constraint.target = o
                    ik_constraint.influence = 1.0
                    bpy.context.view_layer.update()

                    ik_constraint.keyframe_insert(data_path="influence", frame=range_value.start_time)
                    ik_constraint.influence = 1.0
                    ik_constraint.keyframe_insert(data_path="influence", frame=range_value.end_time)
                if src_bone not in bones_to_interpolate:
                    bones_to_interpolate.append(src_bone)

        for bone in bones_to_interpolate:
            self.set_interpolation_keyframes(obj, bone)
        bpy.ops.object.select_all(action='DESELECT')

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
        ik_target_empty_name = self.create_ik_target_name(chain_bone, obj, target_bone,
                                                          target_rig, item.chain_idx)
        o = bpy.data.objects[ik_target_empty_name]
        return chain_bone, o, target_bone, target_rig

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