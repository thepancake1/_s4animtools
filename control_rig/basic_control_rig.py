import math
import os.path

from mathutils import Matrix
import bpy


class CopyBakedAnimationToControlRig(bpy.types.Operator):
    bl_idname = "s4animtools.copy_baked_animation"
    bl_label = "Copy Baked Animation"
    bl_options = {"REGISTER", "UNDO"}

    LEFT_ARM_FK = ["ctrl_l_upperarm_fk", "ctrl_l_forearm_fk", "ctrl_l_hand_fk"]
    RIGHT_ARM_FK = ["ctrl_r_upperarm_fk", "ctrl_r_forearm_fk", "ctrl_r_hand_fk"]
    LEFT_ARM_IK = ["ctrl_l_upperarm_ik", "ctrl_l_forearm_ik", "ctrl_l_hand_ik", "ctrl_L_armpole"]
    RIGHT_ARM_IK = ["ctrl_r_upperarm_ik", "ctrl_r_forearm_ik", "ctrl_r_hand_ik", "ctrl_R_armpole"]
    LEFT_ARM_TARGET = "ctrl_l_hand_target"
    RIGHT_ARM_TARGET = "ctrl_r_hand_target"
    LEFT_ARM_BAKED = ["b__L_UpperArm__", "b__L_Forearm__", "b__L_Hand__"]
    RIGHT_ARM_BAKED = [ "b__R_UpperArm__", "b__R_Forearm__", "b__R_Hand__"]

    LEFT_LEG_FK = ["ctrl_l_thigh_fk", "ctrl_l_calf_fk", "ctrl_l_foot_fk"]
    LEFT_LEG_IK = ["ctrl_l_thigh_ik", "ctrl_l_calf_ik", "ctrl_l_foot_ik", "ctrl_L_legpole"]
    LEFT_LEG_TARGET = "ctrl_l_foot_target"
    LEFT_LEG_BAKED = ["b__L_Thigh__", "b__L_Calf__", "b__L_Foot__"]

    RIGHT_LEG_FK = ["ctrl_r_thigh_fk", "ctrl_r_calf_fk", "ctrl_r_foot_fk"]
    RIGHT_LEG_IK = ["ctrl_r_thigh_ik", "ctrl_r_calf_ik", "ctrl_r_foot_ik", "ctrl_R_legpole"]
    RIGHT_LEG_TARGET = "ctrl_r_foot_target"
    RIGHT_LEG_BAKED = ["b__R_Thigh__", "b__R_Calf__", "b__R_Foot__"]

    def copy_location(self, arm, target, from_target):
        print(f"Copying position from {target} to {from_target.name}")
        copy_constraint = from_target.constraints.new('COPY_LOCATION')
        copy_constraint.target = arm
        copy_constraint.subtarget = target
        return copy_constraint

    def copy_rotation(self, arm, target, from_target):
        print(f"Copying position from {target} to {from_target.name}")
        copy_constraint = from_target.constraints.new('COPY_ROTATION')
        copy_constraint.target = arm
        copy_constraint.subtarget = target
        return copy_constraint

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='POSE', toggle=False)

        bpy.ops.pose.select_all(action='DESELECT')
        constraints = []
        constraints.extend(self.setup_constraints(obj, self.LEFT_ARM_BAKED, self.LEFT_ARM_FK, self.LEFT_ARM_IK, self.LEFT_ARM_TARGET))
        constraints.extend(self.setup_constraints(obj, self.RIGHT_ARM_BAKED, self.RIGHT_ARM_FK, self.RIGHT_ARM_IK, self.RIGHT_ARM_TARGET))
        constraints.extend(self.setup_constraints(obj, self.LEFT_LEG_BAKED, self.LEFT_LEG_FK, self.LEFT_LEG_IK, self.LEFT_LEG_TARGET))
        constraints.extend(self.setup_constraints(obj, self.RIGHT_LEG_BAKED, self.RIGHT_LEG_FK, self.RIGHT_LEG_IK, self.RIGHT_LEG_TARGET))
        bpy.context.view_layer.update()

        bpy.ops.nla.bake(frame_start=context.scene.frame_start, frame_end=context.scene.frame_end, only_selected=True, visual_keying=True, clear_constraints=False, use_current_action=True, bake_types={'POSE'})


        for bone in [*self.LEFT_ARM_BAKED, *self.LEFT_ARM_FK, *self.LEFT_ARM_IK, self.LEFT_ARM_TARGET,
                     *self.RIGHT_ARM_BAKED,*self.RIGHT_ARM_FK, *self.RIGHT_ARM_IK, self.RIGHT_ARM_TARGET,
                     *self.LEFT_LEG_BAKED, *self.LEFT_LEG_FK, *self.LEFT_LEG_IK, self.LEFT_LEG_TARGET,
                     *self.RIGHT_LEG_BAKED,*self.RIGHT_LEG_FK, *self.RIGHT_LEG_IK, self.RIGHT_LEG_TARGET]:
            bone = obj.pose.bones[bone]
            for constraint in constraints:
                try:
                    bone.constraints.remove(constraint)
                except:
                    pass
        bpy.context.view_layer.update()

        self.unmute_copy_bones(obj, self.LEFT_ARM_BAKED)
        self.unmute_copy_bones(obj, self.RIGHT_ARM_BAKED)
        self.unmute_copy_bones(obj, self.LEFT_LEG_BAKED)
        self.unmute_copy_bones(obj, self.RIGHT_LEG_BAKED)



        return {'FINISHED'}

    def setup_constraints(self, obj, baked, fk, ik, target):
        self.mute_copy_bones(obj, baked)
        results = [*self.add_copy_constraints(obj, baked, fk),*self.add_copy_constraints_with_pole(obj, baked, ik, target)]
        return results

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
                constraint.mute = True

    def unmute_copy_bones(self, obj, copy_list):
        for idx in range(0, 3):
            existing_constraints = [c for c in obj.pose.bones[copy_list[idx]].constraints]
            for constraint in existing_constraints:
                constraint.mute = False


class CopyBakedAnimationToControlRigNew(bpy.types.Operator):
    bl_idname = "s4animtools.copy_baked_animation_new"
    bl_label = "Copy Baked Animation"
    bl_options = {"REGISTER", "UNDO"}

    LEFT_HAND_IK = "b__L_Hand__IK"
    RIGHT_HAND_IK = "b__R_Hand__IK"
    LEFT_FOOT_IK = "b__L_Foot__IK"
    RIGHT_FOOT_IK = "b__R_Foot__IK"
    bone_to_pole = {LEFT_HAND_IK:"b__L_ArmExportPole__Helper",
                           RIGHT_HAND_IK:"b__R_ArmExportPole__Helper",
                           LEFT_FOOT_IK:"b__L_LegExportPole__Helper",
                           RIGHT_FOOT_IK:"b__R_LegExportPole__Helper"}

    bone_to_pole_export = {LEFT_HAND_IK: "b__L_Forearm__Export",
                           RIGHT_HAND_IK: "b__R_Forearm__Export",
                           LEFT_FOOT_IK: "b__L_Calf__Export",
                           RIGHT_FOOT_IK: "b__R_Calf__Export"}

    def copy_location(self, arm, from_target, target):
        print(f"Copying position from {target} to {from_target}")
        from_target = arm.pose.bones[from_target]
        copy_constraint = from_target.constraints.new('COPY_LOCATION')
        copy_constraint.head_tail = 1
        copy_constraint.target = arm
        copy_constraint.subtarget = target
        return copy_constraint

    def copy_rotation(self, arm, from_target, target):
        print(f"Copying rotation from {target} to {from_target}")
        from_target = arm.pose.bones[from_target]
        copy_constraint = from_target.constraints.new('COPY_ROTATION')
        copy_constraint.target = arm
        copy_constraint.subtarget = target
        return copy_constraint

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='POSE', toggle=False)

        bpy.ops.pose.select_all(action='DESELECT')

        obj.l_hand_fk_ik = 0.0
        obj.r_hand_fk_ik = 0.0
        obj.l_foot_fk_ik = 0.0
        obj.r_foot_fk_ik = 0.0
        constraints = []
        for bone in [self.LEFT_HAND_IK, self.RIGHT_HAND_IK, self.LEFT_FOOT_IK, self.RIGHT_FOOT_IK]:
            ik_bone = bone
            fk_bone = bone[:-2]
            constraints.extend(self.add_copy_constraints(obj,ik_bone,fk_bone))
            constraints.extend(self.add_copy_constraints(obj, self.bone_to_pole[ik_bone], self.bone_to_pole_export[ik_bone]))

        bpy.ops.nla.bake(frame_start=context.scene.frame_start, frame_end=context.scene.frame_end, only_selected=True, visual_keying=True, clear_constraints=False, use_current_action=True, bake_types={'POSE'})


        for bone in obj.pose.bones:
            for constraint in constraints:
                try:
                    bone.constraints.remove(constraint)
                except:
                    pass
        return {'FINISHED'}


    def add_copy_constraints(self, obj, ik_bone,fk_bone):
        constraints = []

        constraints.append(self.copy_rotation(obj, ik_bone, fk_bone))
        constraints.append(self.copy_location(obj, ik_bone, fk_bone))
        obj.pose.bones[ik_bone].bone.select = True
        return constraints




class CopyLeftSideAnimationToRightSide(bpy.types.Operator):
    bl_idname = "s4animtools.copy_left_side"
    bl_label = "Copy Left Side Animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        action = obj.animation_data.action
        d = ["_bind_DB_blanket_Top_L_", "_bind_DB_blanket_Mid_L_", "_bind_DB_blanket_Bottom_L_",
             "_bind_DB_OpacityPanel_L_", "_bind_DB_blanket_MakeBedFront_L_", "_bind_DB_blanket_MakeBedMid_L_"]
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
                        print(current_value)

        return {"FINISHED"}


class CopyLeftSideAnimationToRightSideSim(bpy.types.Operator):
    bl_idname = "s4animtools.copy_left_side_sim"
    bl_label = "Copy Left Side Animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        action = obj.animation_data.action
        d = ["_bind_DB_blanket_Top_L_", "_bind_DB_blanket_Mid_L_", "_bind_DB_blanket_Bottom_L_",
             "_bind_DB_OpacityPanel_L_", "_bind_DB_blanket_MakeBedFront_L_", "_bind_DB_blanket_MakeBedMid_L_"]
       #for group in action.groups:
       #  #  if group.name.replace("_R_", "_L_") in d:
       #    oldname = group.name

       #    group.name = group.name.replace("_R_", "_R_unused").replace("_r_", "_r_unused")
       #    for fcurve in group.channels:
       #        fcurve.data_path = fcurve.data_path.replace(oldname, oldname.replace("_R_", "_R_unused").replace("_r_", "_r_unused"))



        for group in action.groups:
            #if group.name in d:
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
            for fcurve in group.channels:
                fcurve.data_path = fcurve.data_path.replace(oldname, group.name)

                if "rotation_quaternion" in fcurve.data_path:
                    if fcurve.array_index == 1 or fcurve.array_index == 2:
                        for keyframe in fcurve.keyframe_points:
                            current_value = keyframe.co[1]
                            keyframe.co[1] = current_value * -1
                            print(current_value)


                if "location" in fcurve.data_path:
                    if fcurve.array_index == 2:
                        for keyframe in fcurve.keyframe_points:
                            current_value = keyframe.co[1]
                            keyframe.co[1] = current_value * -1
                            print(current_value)

        return {"FINISHED"}
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
        print(selected_bones)

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
                            print("test")
                            for keyframe in fcurve.keyframe_points:
                                current_value = keyframe.co[1]
                                keyframe.co[1] = current_value * -1
                                print(current_value)


                    if "location" in fcurve.data_path:
                        if fcurve.array_index == 2:
                            for keyframe in fcurve.keyframe_points:
                                current_value = keyframe.co[1]
                                keyframe.co[1] = current_value * -1
                                print(current_value)

        return {"FINISHED"}


class CreateAdvancedControlRig(bpy.types.Operator):
    bl_idname = "s4animtools.create_advanced_control_rig"
    bl_label = "Copy Baked Animation"
    bl_options = {"REGISTER", "UNDO"}

    LEFT_ARM_FK = ["ctrl_l_upperarm_fk", "ctrl_l_forearm_fk", "ctrl_l_hand_fk"]
    RIGHT_ARM_FK = ["ctrl_r_upperarm_fk", "ctrl_r_forearm_fk", "ctrl_r_hand_fk"]
    LEFT_ARM_IK = ["ctrl_l_upperarm_ik", "ctrl_l_forearm_ik", "ctrl_l_hand_ik", "ctrl_L_armpole"]
    RIGHT_ARM_IK = ["ctrl_r_upperarm_ik", "ctrl_r_forearm_ik", "ctrl_r_hand_ik", "ctrl_R_armpole"]
    LEFT_ARM_EXPORT_POLE = "b__L_ArmExportPole__"
    RIGHT_ARM_EXPORT_POLE = "b__R_ArmExportPole__"
    LEFT_LEG_EXPORT_POLE = "b__L_LegExportPole__"
    RIGHT_LEG_EXPORT_POLE = "b__R_LegExportPole__"
    LEFT_ARM_TARGET = "ctrl_l_hand_target"
    RIGHT_ARM_TARGET = "ctrl_r_hand_target"
    LEFT_ARM_BAKED = ["b__L_UpperArm__", "b__L_Forearm__", "b__L_Hand__"]
    RIGHT_ARM_BAKED = ["b__R_UpperArm__", "b__R_Forearm__", "b__R_Hand__"]

    LEFT_LEG_FK = ["ctrl_l_thigh_fk", "ctrl_l_calf_fk", "ctrl_l_foot_fk"]
    LEFT_LEG_IK = ["ctrl_l_thigh_ik", "ctrl_l_calf_ik", "ctrl_l_foot_ik", "ctrl_L_legpole"]
    LEFT_LEG_TARGET = "ctrl_l_foot_target"
    LEFT_LEG_BAKED = ["b__L_Thigh__", "b__L_Calf__", "b__L_Foot__"]

    RIGHT_LEG_FK = ["ctrl_r_thigh_fk", "ctrl_r_calf_fk", "ctrl_r_foot_fk"]
    RIGHT_LEG_IK = ["ctrl_r_thigh_ik", "ctrl_r_calf_ik", "ctrl_r_foot_ik", "ctrl_R_legpole"]
    RIGHT_LEG_TARGET = "ctrl_r_foot_target"
    RIGHT_LEG_BAKED = ["b__R_Thigh__", "b__R_Calf__", "b__R_Foot__"]

    def copy_location(self, arm, target, from_target):
        print(f"Copying position from {target} to {from_target.name}")
        copy_constraint = from_target.constraints.new('COPY_LOCATION')
        copy_constraint.target = arm
        copy_constraint.subtarget = target
        return copy_constraint

    def copy_rotation(self, arm, target, from_target):
        print(f"Copying position from {target} to {from_target.name}")
        copy_constraint = from_target.constraints.new('COPY_ROTATION')
        copy_constraint.target = arm
        copy_constraint.subtarget = target
        return copy_constraint

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)


        self.create_new_ik_chain_from_list(obj.data, self.LEFT_ARM_BAKED, self.LEFT_ARM_FK)
        self.create_new_ik_chain_from_list(obj.data, self.LEFT_ARM_BAKED, self.LEFT_ARM_IK)
        self.create_new_ik_chain_from_list(obj.data, self.RIGHT_ARM_BAKED, self.RIGHT_ARM_FK)
        self.create_new_ik_chain_from_list(obj.data, self.RIGHT_ARM_BAKED, self.RIGHT_ARM_IK)
        self.create_new_ik_chain_from_list(obj.data, self.LEFT_LEG_BAKED, self.LEFT_LEG_FK)
        self.create_new_ik_chain_from_list(obj.data, self.LEFT_LEG_BAKED, self.LEFT_LEG_IK)
        self.create_new_ik_chain_from_list(obj.data, self.RIGHT_LEG_BAKED, self.RIGHT_LEG_FK)
        self.create_new_ik_chain_from_list(obj.data, self.RIGHT_LEG_BAKED, self.RIGHT_LEG_IK)



        bpy.context.view_layer.update()



        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)



        bpy.ops.object.mode_set(mode='POSE', toggle=False)
        self.create_copy_constraints(obj.data, self.LEFT_ARM_BAKED, self.LEFT_ARM_FK)
        self.create_copy_constraints(obj.data, self.LEFT_ARM_BAKED, self.LEFT_ARM_IK, self.LEFT_ARM_TARGET)
        self.create_copy_constraints(obj.data, self.RIGHT_ARM_BAKED, self.RIGHT_ARM_FK)
        self.create_copy_constraints(obj.data, self.RIGHT_ARM_BAKED, self.RIGHT_ARM_IK, self.RIGHT_ARM_TARGET)
        self.create_copy_constraints(obj.data, self.LEFT_LEG_BAKED, self.LEFT_LEG_FK)
        self.create_copy_constraints(obj.data, self.LEFT_LEG_BAKED, self.LEFT_LEG_IK, self.LEFT_LEG_TARGET)
        self.create_copy_constraints(obj.data, self.RIGHT_LEG_BAKED, self.RIGHT_LEG_FK)
        self.create_copy_constraints(obj.data, self.RIGHT_LEG_BAKED, self.RIGHT_LEG_IK, self.RIGHT_LEG_TARGET)
        self.copy_ik_chain_drivers(bpy.context.object, self.LEFT_ARM_BAKED, "l_hand_fk_ik")
        self.copy_ik_chain_drivers(bpy.context.object, self.RIGHT_ARM_BAKED, "r_hand_fk_ik")
        self.copy_ik_chain_drivers(bpy.context.object, self.LEFT_LEG_BAKED, "l_foot_fk_ik")
        self.copy_ik_chain_drivers(bpy.context.object, self.RIGHT_LEG_BAKED, "r_foot_fk_ik")

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        self.create_targets(obj, self.LEFT_ARM_TARGET, self.LEFT_ARM_BAKED[2], self.LEFT_ARM_IK[2])
        self.create_targets(obj, self.RIGHT_ARM_TARGET, self.RIGHT_ARM_BAKED[2], self.RIGHT_ARM_IK[2])

        self.create_poles(obj, self.LEFT_ARM_IK[3], self.LEFT_ARM_EXPORT_POLE, self.LEFT_ARM_IK[2])
        self.create_poles(obj, self.RIGHT_ARM_IK[3], self.RIGHT_ARM_EXPORT_POLE, self.RIGHT_ARM_IK[2])

        self.create_targets(obj, self.LEFT_LEG_TARGET, self.LEFT_LEG_BAKED[2], self.LEFT_LEG_IK[2])
        self.create_targets(obj, self.RIGHT_LEG_TARGET, self.RIGHT_LEG_BAKED[2], self.RIGHT_LEG_IK[2])

        self.create_poles(obj, self.LEFT_LEG_IK[3], self.LEFT_LEG_EXPORT_POLE, self.LEFT_LEG_IK[2])
        self.create_poles(obj, self.RIGHT_LEG_IK[3], self.RIGHT_LEG_EXPORT_POLE, self.RIGHT_LEG_IK[2])
        bpy.context.view_layer.update()
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        return {'FINISHED'}

    def copy_ik_chain_drivers(self,obj, chain_bones, scene_context_ref_switch):
        for bone in chain_bones:
            self.add_driver(obj, obj, f'pose.bones["{bone}"].constraints["Copy Rotation.001"].influence', scene_context_ref_switch)
            bpy.context.view_layer.update()


    def create_new_ik_chain_from_list(self, arm, rigged_bones, chain_bones):
        last_b = None
        for idx, bone_name in enumerate(rigged_bones):
            b = arm.edit_bones[bone_name]
            cb = arm.edit_bones.new(chain_bones[idx])
            cb.head = b.head
            cb.tail = b.tail
            cb.matrix = b.matrix
            cb.parent = b.parent

            if idx != 0:
                cb.parent = last_b
            last_b = cb


    def create_copy_constraints(self, arm, rigged_bones, chain_bones, end_bone=None):
        for idx, bone_name in enumerate(rigged_bones):
            copy_constraint = bpy.context.object.pose.bones[bone_name].constraints.new('COPY_ROTATION')
            copy_constraint.target = bpy.context.object
            if idx == len(rigged_bones) - 1:
                if end_bone is not None:
                    copy_constraint.subtarget = end_bone
                    return

            copy_constraint.subtarget = chain_bones[idx]

    def create_targets(self, arm, target, src_bone, src_ik_bone):
        b = arm.data.edit_bones[src_bone]
        cb = arm.data.edit_bones.new(target)
        cb.head = b.head
        cb.tail = b.tail
        cb.matrix = b.matrix
        cb.parent = b.parent.parent.parent
        bpy.ops.object.mode_set(mode='POSE', toggle=False)

        ik_constraint = arm.pose.bones[src_ik_bone].constraints.new('IK')
        # give it a target bone
        ik_constraint.target = arm
        # note subtarget uses name not object.
        ik_constraint.subtarget = target
        ik_constraint.use_rotation = False
        ik_constraint.chain_count = 3
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    def create_poles(self, arm, target, src_bone, src_ik_bone):
        b = arm.data.edit_bones[src_bone]
        cb = arm.data.edit_bones.new(target)
        cb.head = b.head
        cb.tail = b.tail
        cb.matrix = b.matrix
        cb.parent = b.parent.parent.parent
        bpy.ops.object.mode_set(mode='POSE', toggle=False)

        ik_constraint = arm.pose.bones[src_ik_bone].constraints[0]
        # give it a target bone
        ik_constraint.pole_target = arm
        # note subtarget uses name not object.
        ik_constraint.pole_subtarget = target
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    def add_driver(
            self, source, target, prop, dataPath,
            index=-1, negative=False, func=''
    ):
        ''' Add driver to source prop (at index), driven by target dataPath '''

        if index != -1:
            d = source.driver_add(prop, index).driver
        else:
            d = source.driver_add(prop).driver
        d.type = "AVERAGE"

        v = d.variables.new()
        v.name = "prop"
        v.targets[0].id = target
        v.targets[0].data_path = dataPath

       # d.expression = func + "(" + v.name + ")" if func else v.name
       # d.expression = d.expression if not negative else "-1 * " + d.expression
