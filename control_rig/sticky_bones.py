# use typing for type hints
import bpy
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import s4animtools.ik_manager


def create_childof_constraint_obj(src_obj, to_obj, to_bone):
    constraint = src_obj.constraints.new("CHILD_OF")
    constraint.target = to_obj
    constraint.subtarget = to_bone
    constraint.name = "IK Child Of"
    return constraint


def create_location_constraint(src_obj, src_bone, to_bone):
    constraint = to_bone.constraints.new("COPY_LOCATION")
    constraint.target = src_obj
    constraint.subtarget = src_bone
    constraint.name = "IK Copy Location"
    return constraint

def create_rotation_constraint(src_obj, src_bone_name, to_bone):
    constraint = to_bone.constraints.new("COPY_ROTATION")
    constraint.target = src_obj
    constraint.subtarget = src_bone_name
    constraint.target_space = "LOCAL_WITH_PARENT"
    constraint.owner_space = "LOCAL_WITH_PARENT"
    constraint.name = "IK Copy Rotation"
    return constraint

def create_ik_constraint(src_obj, src_bone_name, to_bone, pole_bone_name):
    constraint = to_bone.constraints.new("IK")
    constraint.target = src_obj
    constraint.subtarget = src_bone_name
    constraint.name = "IK Chain Constraint"
    constraint.chain_count = 3
    constraint.use_rotation = False
    constraint.pole_target = src_obj
    constraint.pole_subtarget = pole_bone_name
    return constraint


def create_stretchto_constraint(src_obj, src_bone_name, to_bone):
    constraint = to_bone.constraints.new("STRETCH_TO")
    constraint.target = src_obj
    constraint.subtarget = src_bone_name
    constraint.rest_length = 0.5
    constraint.name = "IK Chain Pole Indicator Stretch"
    constraint.keep_axis = "PLANE_X"
    return constraint


def create_dampedtrack_constraint(src_obj, src_bone_name, to_bone):
    constraint = to_bone.constraints.new("DAMPED_TRACK")
    constraint.target = src_obj
    constraint.subtarget = src_bone_name
    constraint.track_axis = "TRACK_Y"
    constraint.name = "Eyes Damped Track"
    return constraint


def duplicate_bone(obj, bone_name, new_bone_name, parent_bone_name=None):
    if obj is None:
        raise ValueError("Object is None.")
    if obj.type != 'ARMATURE':
        raise ValueError("Object is not an armature.")
    existing_bone = obj.data.edit_bones[bone_name]
    if new_bone_name in obj.data.edit_bones:
        raise ValueError(f"Bone with name {new_bone_name} already exists.")
    if parent_bone_name and parent_bone_name not in obj.data.edit_bones:
        raise ValueError(f"Parent bone {parent_bone_name} does not exist.")
    new_bone = obj.data.edit_bones.new(new_bone_name)
    new_bone.head = existing_bone.head
    new_bone.tail = existing_bone.tail
    new_bone.roll = existing_bone.roll
    if parent_bone_name is None:
        new_bone.parent = None
    else:
        new_bone.parent = obj.data.edit_bones[parent_bone_name]

    return obj.data.edit_bones[new_bone_name]


def add_driver(
        source, target, prop, data_path,
        index=-1, negative=False, func=''
):
    ''' Add driver to source prop (at index), driven by target dataPath '''

    if index != -1:
        d = source.driver_add(prop, index).driver
    else:
        d = source.driver_add(prop).driver
    for value in d.variables:
        d.variables.remove(value)
    v = d.variables.new()

    v.name = prop
    v.targets[0].id_type = "OBJECT"
    v.targets[0].id = target
    v.targets[0].data_path = data_path

    d.expression = func if func else v.name
    d.expression = d.expression if not negative else "-1 * " + d.expression


class OT_S4ANIMTOOLS_EditIKTarget(bpy.types.Operator):
    """Delete an ik target."""
    bl_idname = "s4animtools.edit_ik_target"
    bl_label = "Edit an IK Target"
    bl_options = {"REGISTER", "UNDO"}

    command: bpy.props.StringProperty()

    def execute(self, context):
        if not self.command.isdigit():
            return {'CANCELLED'}
      #  ik_target_info
        ik_target_info = context.object.ik_targets[int(self.command)]
        if ik_target_info is None:
            self.report({'ERROR'}, "No IK Target found.")
            return {'CANCELLED'}

        # Create an empty, then add a copy transform constraint to the empty
        bpy.ops.object.mode_set(mode="OBJECT")
        current_obj = context.object
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.object.empty_add(type='PLAIN_AXES')
        empty = context.active_object
        empty.name = "{}_{}_{}".format(current_obj.name, ik_target_info.chain_bone, self.command) + "_target"
        empty.empty_display_size = 0.2
        if ik_target_info.target_obj not in bpy.data.objects:
            self.report({'ERROR'}, "Target object not found.")
            return {'CANCELLED'}
        if ik_target_info.target_bone not in bpy.data.objects[ik_target_info.target_obj].pose.bones:
            self.report({'ERROR'}, "Target bone not found.")
            return {'CANCELLED'}
        target_obj = bpy.data.objects[ik_target_info.target_obj]
        create_childof_constraint_obj(empty, target_obj, ik_target_info.target_bone)


        return {'FINISHED'}