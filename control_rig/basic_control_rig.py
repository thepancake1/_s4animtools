
import bpy
from mathutils import Vector, Quaternion
class CopyLeftSideAnimationToRightSide(bpy.types.Operator):
    bl_idname = "s4animtools.copy_left_side"
    bl_label = "Copy Left Side Animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        action = obj.animation_data.action
        for group in action.groups:
          #  if group.name.replace("_R_", "_L_") in d:
            oldname = group.name

            group.name = group.name.replace("_R_", "_R_unused").replace("_r_", "_r_unused")
            for fcurve in group.channels:
                fcurve.data_path = fcurve.data_path.replace(oldname, oldname.replace("_R_", "_R_unused").replace("_r_", "_r_unused"))



        for group in action.groups:
            #if group.name in d:
            oldname = group.name

            group.name = group.name.replace("_L_", "_R_temp").replace("_l_", "_r_temp")
            for fcurve in group.channels:
                fcurve.data_path = fcurve.data_path.replace(oldname, oldname.replace("_L_", "_R_temp").replace("_l_", "_r_temp"))

        for group in action.groups:
           # if group.name.endswith("temp"):
            oldname = group.name
            group.name = group.name.replace("temp", "")
            for fcurve in group.channels:
                fcurve.data_path = fcurve.data_path.replace(oldname, group.name)

               # if "location" in fcurve.data_path and fcurve.array_index == 2:
               #     print("test")
               #     for keyframe in fcurve.keyframe_points:
               #         current_value = keyframe.co[1]
               #         keyframe.co[1] = current_value * -1
               #         print(current_value)

                if "rotation_quaternion" in fcurve.data_path and fcurve.array_index == 2 or fcurve.array_index == 3:
                    print("test")
                    for keyframe in fcurve.keyframe_points:
                        current_value = keyframe.co[1]
                        keyframe.co[1] = current_value * -1
                        #print(current_value)

                if "rotation_euler" in fcurve.data_path:
                    for keyframe in fcurve.keyframe_points:
                        current_value = keyframe.co[1]
                        keyframe.co[1] = current_value * -1
        return {"FINISHED"}
class CopyLeftSideAnimationToRightSideSim(bpy.types.Operator):
    bl_idname = "s4animtools.copy_left_side_sim"
    bl_label = "Copy Left Side Animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        action = obj.animation_data.action

        for group in action.groups:
            oldname = group.name


            if "_L_" in group.name or "_l_" in group.name:
                group.name = group.name.replace("_L_", "_R_temp").replace("_l_", "_r_temp")
            elif "_R_" in group.name or "_r_" in group.name:
                group.name = group.name.replace("_R_", "_L_temp").replace("_r_", "_l_temp")
                for fcurve in group.channels:
                    action.fcurves.remove(fcurve)
            if "temp" not in group.name:
                group.name = group.name + "temp"


        for group in action.groups:
            oldname = group.name
            group.name = group.name.replace("temp", "")

            print(group.name, oldname)
            for fcurve in group.channels:
                fcurve.data_path = fcurve.data_path.replace(oldname, group.name)
                if "_R_" in group.name:
                    pass
                else:
                    continue
                if "rotation_euler" in fcurve.data_path:
                    multiplier = 1
                    for keyframe in fcurve.keyframe_points:
                        current_value = keyframe.co[1]
                        if "Hand" in fcurve.data_path:
                            multiplier = -1
                        keyframe.co[1] = current_value * multiplier

                if "location" in fcurve.data_path:
                    multiplier = 1
                    if "Foot" in fcurve.data_path or "LegExport" in fcurve.data_path:
                        multiplier = -1
                    if fcurve.array_index == 2:
                        for keyframe in fcurve.keyframe_points:
                            current_value = keyframe.co[1]
                            keyframe.co[1] = current_value * multiplier
        fcurves = obj.animation_data.action.fcurves
        for fcurve in fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'
        return {"FINISHED"}

class FlipLeftSideAnimationToRightSideSim(bpy.types.Operator):
    bl_idname = "s4animtools.flip_left_side_sim"
    bl_label = "Flip Left Side Animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        action = obj.animation_data.action

        for group in action.groups:
            oldname = group.name


            if "_L_" in group.name or "_l_" in group.name:
                group.name = group.name.replace("_L_", "_R_temp").replace("_l_", "_r_temp")
            elif "_R_" in group.name or "_r_" in group.name:
                group.name = group.name.replace("_R_", "_L_temp").replace("_r_", "_l_temp")

            if "temp" not in group.name:
                group.name = group.name + "temp"
            for fcurve in group.channels:
                fcurve.data_path = fcurve.data_path.replace(oldname,group.name)

        for group in action.groups:
            oldname = group.name
            group.name = group.name.replace("temp", "")

            print(group.name, oldname)
            for fcurve in group.channels:
                fcurve.data_path = fcurve.data_path.replace(oldname, group.name)

                if "rotation_quaternion" in fcurve.data_path:
                    if fcurve.array_index == 1 or fcurve.array_index == 2:
                        for keyframe in fcurve.keyframe_points:
                            current_value = keyframe.co[1]
                            keyframe.co[1] = current_value * -1
                if "rotation_euler" in fcurve.data_path:
                    multiplier = 1
                    if fcurve.array_index == 1:
                        multiplier = -1
                    for keyframe in fcurve.keyframe_points:
                        current_value = keyframe.co[1]
                        keyframe.co[1] = current_value * multiplier

                            #print(current_value)

                if "_L_" in group.name or "_R_" in group.name:
                    pass
                else:
                    continue
                if "rotation_euler" in fcurve.data_path:
                    multiplier = 1
                    if "Hand" in fcurve.data_path:
                        multiplier = -1
                    for keyframe in fcurve.keyframe_points:
                        current_value = keyframe.co[1]

                        keyframe.co[1] = current_value * multiplier

                if "location" in fcurve.data_path:
                    multiplier = 1
                    if "Foot" in fcurve.data_path or "LegExport" in fcurve.data_path:
                        multiplier = -1
                    if fcurve.array_index == 2:
                        for keyframe in fcurve.keyframe_points:
                            current_value = keyframe.co[1]
                            keyframe.co[1] = current_value * multiplier
        fcurves = obj.animation_data.action.fcurves
        for fcurve in fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'
        return {"FINISHED"}


class AdjustProportionsOfControlRigToTargetRig(bpy.types.Operator):
    bl_idname = "s4animtools.adjust_proportions_of_control_rig_to_target_rig"
    bl_label = "Adjust Proportions of Control Rig to Target Rig"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        import bpy

        rig_name = "x"

        source_rig = bpy.data.objects["x.001"]

        target_rig = bpy.data.objects[rig_name]
        bpy.ops.object.mode_set(mode='EDIT')

        for bone in target_rig.data.edit_bones:
            for source_bone in source_rig.data.edit_bones:

                if source_bone.name == bone.name:
                    bone.head = source_bone.head
                    bone.tail = source_bone.tail

        bpy.ops.object.mode_set(mode='OBJECT')



class CopySelectedLeftSideToRightSide(bpy.types.Operator):
    bl_idname = "s4animtools.copy_left_side_sim_selected"
    bl_label = "Copy Left Side Animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        action = obj.animation_data.action

        selected_bones = bpy.context.selected_pose_bones
        selected_bones = [x.name for x in selected_bones]
        for item in selected_bones[:]:
            selected_bones.append(item.replace("_L_", "_R_").replace("_l_", "_r_"))
       # print(selected_bones)

        for group in action.groups:

            oldname = group.name


            if "_L_" in group.name or "_l_" in group.name:
                group.name = group.name.replace("_L_", "_R_temp").replace("_l_", "_r_temp")
            elif "_R_" in group.name or "_r_" in group.name:
                group.name = group.name.replace("_R_", "_L_temp").replace("_r_", "_l_temp")
            if group.name in selected_bones:

                if "temp" not in group.name:
                    group.name = group.name + "temp"
                for fcurve in group.channels:
                    fcurve.data_path = fcurve.data_path.replace(oldname,group.name)

        for group in action.groups:
           # if group.name.endswith("temp"):
            oldname = group.name
            group.name = group.name.replace("temp", "")
            if group.name in selected_bones:
                for fcurve in group.channels:
                    fcurve.data_path = fcurve.data_path.replace(oldname, group.name)
                    print(fcurve.data_path)


                    if "rotation_quaternion" in fcurve.data_path:
                        if fcurve.array_index == 1 or fcurve.array_index == 2:
                            #print("test")
                            for keyframe in fcurve.keyframe_points:
                                current_value = keyframe.co[1]
                                keyframe.co[1] = current_value * -1
                                #print(current_value)

                    if "rotation_euler" in fcurve.data_path:
                            for keyframe in fcurve.keyframe_points:
                                current_value = keyframe.co[1]
                                keyframe.co[1] = current_value * -1
                    if "location" in fcurve.data_path:
                        if fcurve.array_index == 2:
                            for keyframe in fcurve.keyframe_points:
                                current_value = keyframe.co[1]
                                keyframe.co[1] = current_value * -1
                                #print(current_value)

        return {"FINISHED"}
class CopyBakedAnimationToControlRig(bpy.types.Operator):
    bl_idname = "s4animtools.copy_baked_animation"
    bl_label = "Copy Baked Animation"
    bl_options = {"REGISTER", "UNDO"}

    LEFT_HAND = "b__L_Hand__"
    RIGHT_HAND = "b__R_Hand__"
    LEFT_FOOT = "b__L_Foot__"
    RIGHT_FOOT = "b__R_Foot__"

    LEFT_ARM_TARGET = LEFT_HAND + "Hold"
    RIGHT_ARM_TARGET = RIGHT_HAND + "Hold"

    LEFT_ARM_IK = LEFT_HAND + "IK"
    RIGHT_ARM_IK = RIGHT_HAND + "IK"

    LEFT_LEG_IK = LEFT_FOOT + "IK"
    RIGHT_LEG_IK = RIGHT_FOOT + "IK"

    LEFT_ARM_BAKED = ["b__L_UpperArm__", "b__L_Forearm__", LEFT_HAND]
    RIGHT_ARM_BAKED = [ "b__R_UpperArm__", "b__R_Forearm__", RIGHT_HAND]

    LEFT_ARM_POLE = "b__L_ArmExportPole__"
    RIGHT_ARM_POLE = "b__R_ArmExportPole__"

    LEFT_LEG_POLE = "b__L_LegExportPole__"
    RIGHT_LEG_POLE = "b__R_LegExportPole__"

    LEFT_LEG_TARGET = LEFT_FOOT + "Hold"
    RIGHT_LEG_TARGET = RIGHT_FOOT + "Hold"
    LEFT_LEG_BAKED = ["b__L_Thigh__", "b__L_Calf__", LEFT_FOOT]
    RIGHT_LEG_BAKED = ["b__R_Thigh__", "b__R_Calf__", RIGHT_FOOT]

    def copy_location(self, arm, target, from_target):
        print(f"Copying position from {target.name} to {from_target.name}")
        copy_constraint = from_target.constraints.new('COPY_LOCATION')
        copy_constraint.target = arm
        copy_constraint.subtarget = target.name
        return copy_constraint

    def copy_rotation(self, arm, target, from_target):
        print(f"Copying position from {target.name} to {from_target.name}")
        copy_constraint = from_target.constraints.new('COPY_ROTATION')
        copy_constraint.target = arm
        copy_constraint.subtarget = target.name
        return copy_constraint

    def execute(self, context):
        obj = bpy.context.object
        animation_data = obj.animation_data

        bpy.ops.object.mode_set(mode='POSE', toggle=False)

        bpy.ops.pose.select_all(action='DESELECT')
        constraints = []
        IK_suffix = "IK"
        self.add_single_copy_constraint(obj, context.object.pose.bones[self.LEFT_HAND],
                                        context.object.pose.bones[self.LEFT_ARM_IK])
        self.mute_all_constraints(context.object.pose.bones[self.LEFT_HAND])
        self.mute_all_constraints(context.object.pose.bones[self.LEFT_ARM_TARGET])

        self.add_single_copy_constraint(obj, context.object.pose.bones[self.RIGHT_HAND],
                                        context.object.pose.bones[self.RIGHT_ARM_IK])
        self.mute_all_constraints(context.object.pose.bones[self.RIGHT_HAND])
        self.mute_all_constraints(context.object.pose.bones[self.RIGHT_ARM_TARGET])

        self.add_single_copy_constraint(obj, context.object.pose.bones[self.LEFT_FOOT],
                                        context.object.pose.bones[self.LEFT_LEG_IK])
        self.mute_all_constraints(context.object.pose.bones[self.LEFT_FOOT])
        self.mute_all_constraints(context.object.pose.bones[self.LEFT_LEG_TARGET])

        self.add_single_copy_constraint(obj, context.object.pose.bones[self.RIGHT_FOOT],
                                        context.object.pose.bones[self.RIGHT_LEG_IK])
        self.mute_all_constraints(context.object.pose.bones[self.RIGHT_FOOT])
        self.mute_all_constraints(context.object.pose.bones[self.RIGHT_LEG_TARGET])

        bpy.ops.nla.bake(frame_start=context.scene.frame_start, frame_end=context.scene.frame_end, only_selected=True,
                         visual_keying=True, clear_constraints=True, use_current_action=True, bake_types={'POSE'})
        self.unmute_all_constraints(context.object.pose.bones[self.LEFT_ARM_TARGET])
        self.unmute_all_constraints(context.object.pose.bones[self.LEFT_HAND])
        self.unmute_all_constraints(context.object.pose.bones[self.RIGHT_ARM_TARGET])
        self.unmute_all_constraints(context.object.pose.bones[self.RIGHT_HAND])
        self.unmute_all_constraints(context.object.pose.bones[self.LEFT_LEG_TARGET])
        self.unmute_all_constraints(context.object.pose.bones[self.LEFT_FOOT])
        self.unmute_all_constraints(context.object.pose.bones[self.RIGHT_LEG_TARGET])
        self.unmute_all_constraints(context.object.pose.bones[self.RIGHT_FOOT])
        return {'FINISHED'}

    def mute_all_constraints(self, pose_bone):
        constraints = [c for c in pose_bone.constraints]
        for constraint in constraints:
            constraint.mute = True


    def unmute_all_constraints(self, pose_bone):
        constraints = [c for c in pose_bone.constraints]
        for constraint in constraints:
            constraint.mute = False
    def setup_constraints(self, obj, baked, ik, target):
        self.mute_copy_bones(obj, baked)
        results = [*self.add_copy_constraints_with_pole(obj, baked, ik, target)]
        return results

    def add_hold_copy_constraints(self, obj, bone_to_copy_from, target_bone, chain_bones):
        self.mute_copy_bones(obj, chain_bones)
        return self.add_single_copy_constraint(obj, bpy.context.object.pose.bones[bone_to_copy_from],
                                               bpy.context.object.pose.bones[target_bone])

    def add_single_copy_constraint(self, obj, bone_tocopy_from, target_bone):
        constraints = list()
        constraints.append(self.copy_location(obj, bone_tocopy_from, target_bone))
        constraints.append(self.copy_rotation(obj, bone_tocopy_from, target_bone))

        target_bone.bone.select = True
        return constraints

    def add_copy_constraints(self, obj, baked, fk):
        constraints = []
        for idx in range(0, 3):
            fk_bone = obj.pose.bones[fk[idx]]
            constraints.append(self.copy_rotation(obj, baked[idx], fk_bone))
            fk_bone.bone.select = True
        return constraints

    def add_copy_constraints_with_pole(self, obj, baked, ik, target):
        ik_bone = obj.pose.bones[target]
        ik_bone.bone.select = True
        obj.pose.bones[ik[3]].bone.select = True
        return self.copy_location(obj, baked[2], obj.pose.bones[target]), self.copy_location(obj, baked[1], obj.pose.bones[ik[3]]), \
                self.copy_rotation(obj, baked[1], obj.pose.bones[ik[3]]), self.copy_rotation(obj, baked[2], obj.pose.bones[target])


    def mute_copy_bones(self, obj, copy_list):
        for idx in range(0, 3):
            existing_constraints = [c for c in obj.pose.bones[copy_list[idx]].constraints]
            for constraint in existing_constraints:
                obj.pose.bones[copy_list[idx]].constraints.remove(constraint)

    def unmute_copy_bones(self, obj, copy_list):
        for idx in range(0, 3):
            existing_constraints = [c for c in obj.pose.bones[copy_list[idx]].constraints]
            for constraint in existing_constraints:
                constraint.mute = False
