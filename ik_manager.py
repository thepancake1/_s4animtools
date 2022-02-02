import bpy
from _s4animtools.ik_baker import s4animtool_OT_bakeik, get_ik_targets

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
            context.object.ik_targets[-1].target_obj = context.object.name
            context.object.ik_targets[-1].target_bone = "b__ROOT__"



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