import bpy
from _s4animtools.ik_baker import s4animtool_OT_bakeik, get_ik_targets
MAX_SUBROOTS = 180

class BeginIKMarker(bpy.types.Operator):
    """Move the currently selected script item."""
    bl_idname = "s4animtools.beginikmarker"
    bl_label = "beginikmarker"
    bl_options = {"REGISTER", "UNDO"}

    command: bpy.props.StringProperty()

    def execute(self, context):

        if len(context.selected_pose_bones) != 1:
            raise Exception("You can only select one bone as a target.")

        chain_bone = None
        holder_bone = None
        self.side, self.grip,self.begin = self.command.split(",")
        found = False

        if self.side == "LEFT":
            if self.grip == "HAND":
                chain_bone = "b__L_Hand__"
                holder_bone = "Left Grip"

            elif self.grip == "FOOT":
                chain_bone = "b__L_Foot__"
                holder_bone = "Left Foot"


        elif self.side == "RIGHT":
            if self.grip == "HAND":
                chain_bone = "b__R_Hand__"
                holder_bone = "Right Grip"

            elif self.grip == "FOOT":
                chain_bone = "b__R_Foot__"
                holder_bone = "Right Foot"

        if self.grip == "BIND":
            chain_bone = "b__ROOT_bind__"
            holder_bone = "b__ROOT_bind__"

        #print(self.side,self.grip)
        if self.begin == "BEGIN":


            found=False

            for idx, item in enumerate(get_ik_targets(obj)):
                if item.target_bone == context.selected_pose_bones[0].name:
                    if item.target_obj == context.object.name:
                        if item.chain_bone == chain_bone:
                            found = True
                            break

            if not found:
                if self.begin == "BEGIN":
                    context.object.ik_targets.add()
                idx = len(context.object.ik_targets) - 1
            context.object.ik_targets[idx].ranges.add()
            context.object.ik_targets[idx].ranges[-1].start_time = context.scene.frame_current
            context.object.ik_targets[idx].ranges[-1].end_time = context.scene.frame_current
            context.object.ik_targets[idx].chain_bone = chain_bone
            context.object.ik_targets[idx].target_obj = context.object.name
            context.object.ik_targets[idx].target_bone = context.selected_pose_bones [0].name

            context.object.ik_idx += 1
        else:
            for idx, item in enumerate(context.object.ik_targets):
                if item.target_bone == context.selected_pose_bones[0].name:
                    if item.target_obj == context.object.name:
                        if item.chain_bone == chain_bone:
                            found = True
                            break
            if not found:
                idx = len(context.object.ik_targets) - 1
            context.object.ik_targets[idx].ranges[-1].end_time = context.scene.frame_current
        context.object.ik_idx = min(max(context.object.ik_idx, 0), len(context.object.ik_targets) - 1)
        context.area.tag_redraw()
        return {'FINISHED'}


class LIST_OT_NewIKRange(bpy.types.Operator):
    """Add a new ik range item to the list."""
    bl_idname = "iktarget.new_ik_range"
    bl_label = "Add a new item"
    bl_options = {"REGISTER", "UNDO"}

    command: bpy.props.StringProperty()
    def execute(self, context):
        if str(self.command).isdigit():
            context.object.ik_targets[int(self.command)].ranges.add()

        return {'FINISHED'}



class LIST_OT_DeleteIKRange(bpy.types.Operator):
    """Add a new ik range item to the list."""
    bl_idname = "iktarget.delete_ik_range"
    bl_label = "Delete ik range"
    bl_options = {"REGISTER", "UNDO"}

    command: bpy.props.StringProperty()
    def execute(self, context):
        target_idx, range_idx = self.command.split(",")
        if str(target_idx).isdigit():
            if str(range_idx).isdigit():
                context.object.ik_targets[int(target_idx)].ranges.remove(int(range_idx))

        return {'FINISHED'}




class LIST_OT_NewIKTarget(bpy.types.Operator):
    """Add a new ik target item to the list."""
    bl_idname = "iktarget.new"
    bl_label = "Add a new item"
    bl_options = {"REGISTER", "UNDO"}

    command: bpy.props.StringProperty()

    def execute(self, context):

        context.object.ik_targets.add()
        context.object.ik_targets[-1].ranges.add()
        context.object.ik_idx = len(context.object.ik_targets)
        context.object.ik_targets[-1].chain_bone = self.command
        context.object.ik_targets[-1].target_obj = context.object.name


        return {'FINISHED'}

class LIST_OT_CreateIKTarget(bpy.types.Operator):
    """Add roots to the list."""
    bl_idname = "iktarget.create_roots"
    bl_label = "Add a new item"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        chain_bones  = ["b__L_Hand__", "b__R_Hand__", "b__L_Foot__", "b__R_Foot__", "b__ROOT_bind__"]

        for i in range(5):
            context.object.ik_targets.add()
            context.object.ik_targets[-1].ranges.add()
            context.object.ik_idx = len(context.object.ik_targets)
            context.object.ik_targets[-1].chain_bone = chain_bones[i]
            if "__subroot__" in context.object.world_bone and context.object.use_world_bone_as_root:
                context.object.ik_targets[-1].target_obj = context.object.world_rig
            else:
                context.object.ik_targets[-1].target_obj = context.object.name
            if "__subroot__" in context.object.world_bone and context.object.use_world_bone_as_root:
                target_bone = context.object.world_bone
                context.object.ik_targets[-1].target_bone = target_bone

            else:
                context.object.ik_targets[-1].target_bone = "b__ROOT__"
            context.object.ik_targets[-1].ranges[-1].end_time = context.scene.frame_end



        return {'FINISHED'}
class LIST_OT_DeleteIKTarget(bpy.types.Operator):
    """Delete an ik target."""
    bl_idname = "iktarget.delete"
    bl_label = "Delete an item"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.object.ik_targets.remove(context.object.ik_idx)
        context.object.ik_idx = min(max(context.object.ik_idx, 0), len(context.object.ik_targets) - 1)

        return {'FINISHED'}

class LIST_OT_DeleteSpecificIKTarget(bpy.types.Operator):
    """Delete an ik target."""
    bl_idname = "iktarget.delete_specific"
    bl_label = "Delete an item"
    bl_options = {"REGISTER", "UNDO"}

    command: bpy.props.StringProperty()

    def execute(self, context):
        if str(self.command).isdigit():
            context.object.ik_targets.remove(int(self.command))
        return {'FINISHED'}

class LIST_OT_MoveIKTarget(bpy.types.Operator):
    """Move the currently selected script item."""
    bl_idname = "iktarget.move"
    bl_label = "Delete an item"
    bl_options = {"REGISTER", "UNDO"}

    direction: bpy.props.EnumProperty(items=(('UP', 'Up', ""), ('DOWN', 'Down', ""),))

    def execute(self, context):
        if self.direction == "UP":
            context.object.ik_idx -= 1
        elif self.direction == "DOWN":
            context.object.ik_idx += 1
        context.object.ik_idx = min(max(context.object.ik_idx, 0), len(context.object.ik_targets) - 1)
        return {'FINISHED'}


class s4animtool_OT_removeIK(bpy.types.Operator):
    """Remove the IK weights"""
    bl_idname = "s4animtools.removeik"
    bl_label = "Remove ik"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s4animtool_OT_bakeik.remove_IK(context.object)
        for bone in context.object.pose.bones:
            for constraint in bone.constraints:
                if not constraint.name.startswith("IKFollow"):
                    constraint.mute = False
        return {'FINISHED'}

class s4animtools_OT_guessTarget(bpy.types.Operator):
    """Remove the IK weights"""
    bl_idname = "s4animtools.guesstarget"
    bl_label = "Guess IK Target"
    bl_options = {"REGISTER", "UNDO"}
    command: bpy.props.StringProperty()

    def execute(self, context):
        src_bone, target_rig_name = self.command.split(",")
        x = context.object
        y = bpy.data.objects[target_rig_name]
        active_pose_bone = x.pose.bones[src_bone]
        disallowed_bones = ["b__L_HandDangle_slot", "b__R_HandDangle_slot"]
        # if targeting self rig, disable ik targets on the same arm. So Left hand won't target left arm slots
        if y == context.object:
            if "b__L_Hand__" == src_bone:
                disallowed_bones.extend(["b__L_Bracelet_slot", "b__L_Ring_slot"])
            elif "b__R_Hand__" == src_bone:
                disallowed_bones.extend(["b__R_Bracelet_slot", "b__R_Ring_slot"])
            elif "b__L_Foot__" == src_bone or "b__R_Foot__" == src_bone:
                disallowed_bones.extend(["b__L_frontCalfTarget_slot", "b__L_inCalfTarget_slot", "b__L_KneeTarget_slot",
                                         "b__L_outThighTarget_slot", "b__L_ThighFrontTarget_slot", "b__L_ThighTarget_slot"])
                disallowed_bones.extend(["b__R_frontCalfTarget_slot", "b__R_inCalfTarget_slot", "b__R_KneeTarget_slot",
                                         "b__R_outThighTarget_slot", "b__R_ThighFrontTarget_slot", "b__R_ThighTarget_slot"])
            elif "b__ROOT_bind__" == src_bone:
                disallowed_bones = [bone.name for bone in x.pose.bones]
        y_scores = {}
        y_translations = {}
        lowest_distance = 100
        for bone in y.pose.bones:
            if bone.name.endswith("slot") and bone.name not in disallowed_bones:
                target_matrix_final = y.matrix_world @ bone.matrix
                active_bone_matrix_final = x.matrix_world @ active_pose_bone.matrix

                distance_of_bone = (active_bone_matrix_final.translation - target_matrix_final.translation).length
                y_scores[bone.name] = distance_of_bone
                y_translations[bone.name] = target_matrix_final.translation
                if distance_of_bone < lowest_distance:
                    lowest_distance = distance_of_bone
        try:
            top_y_bone = sorted(y_scores.items(), key=lambda x: x[1])[0][0]
        except:
            top_y_bone = ""
        print(y_scores.items())
        if lowest_distance > 0.15:
            top_y_bone = ""
        for new_idx, ik_target in enumerate(x.ik_targets):
            if ik_target.chain_bone == src_bone:
                if ik_target.target_bone == "":
                    ik_target.target_bone = top_y_bone

        return {'FINISHED'}

class s4animtool_OT_mute_ik(bpy.types.Operator):
    """Remove the IK weights"""
    bl_idname = "s4animtools.muteik"
    bl_label = "Remove ik"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        for bone in context.object.pose.bones:
            for constraint in bone.constraints:
                if constraint.name.startswith("IKFollow"):
                    constraint.mute = True
        return {'FINISHED'}


class s4animtool_OT_unmute_ik(bpy.types.Operator):
    """Remove the IK weights"""
    bl_idname = "s4animtools.unmuteik"
    bl_label = "Remove ik"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        for bone in context.object.pose.bones:
            for constraint in bone.constraints:
                if constraint.name.startswith("IKFollow"):
                    constraint.mute = False
        return {'FINISHED'}