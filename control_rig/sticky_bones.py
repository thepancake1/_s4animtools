# use typing for type hints
import bpy
from typing import TYPE_CHECKING

from s4animtools.ik_baker import get_ik_target_idx_for_slot_assignment_on_chain
from sims_toolkit.blender.ik_chains import mirror_bone_name

if TYPE_CHECKING:
    import s4animtools.ik_manager

def create_childof_constraint_bone(src_obj, to_obj, src_bone, to_bone):
    constraint = src_bone.constraints.new("CHILD_OF")
    constraint.target = to_obj
    constraint.subtarget = to_bone
    constraint.name = "IK Child Of"

    try:
        bpy.context.view_layer.objects.active = src_obj
        bpy.context.active_object.data.bones.active = src_bone.bone
        with bpy.context.temp_override(active_object=src_obj):

            bpy.ops.constraint.childof_clear_inverse(
                constraint=constraint.name,
                owner='BONE'
            )
    except RuntimeError:
        print("Could not automatically set inverse matrix")

    return constraint

def create_childof_constraint_obj(src_obj, to_obj, to_bone):
    constraint = src_obj.constraints.new("CHILD_OF")
    constraint.target = to_obj
    constraint.subtarget = to_bone
    constraint.name = "IK Child Of"

    try:
        bpy.context.view_layer.objects.active = src_obj
        #src_obj.data.bones.active = src_obj.data.bones[to_bone]
        #src_obj.data.bones[to_bone].select = True
        with bpy.context.temp_override(active_object=src_obj):

            bpy.ops.constraint.childof_clear_inverse(
                constraint=constraint.name,
                owner='OBJECT'
            )
    except RuntimeError:
        print("Could not automatically set inverse matrix")

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



def create_rotation_constraint_worldspace(src_obj, src_bone_name, to_bone):
    constraint = to_bone.constraints.new("COPY_ROTATION")
    constraint.target = src_obj
    constraint.subtarget = src_bone_name
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


def preview_slot_assignment(operator, current_obj, combined_slot_idx):
    ik_target_info = current_obj.ik_targets[combined_slot_idx]
    if ik_target_info is None:
        operator.report({'ERROR'}, "No IK Target found.")
        return {'CANCELLED'}

    # Create an empty, then add a copy transform constraint to the empty
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action='DESELECT')
    # bpy.ops.object.empty_add(type='PLAIN_AXES')
    # empty = context.active_object

    # empty.name = "{}_{}_{}".format(current_obj.name, ik_target_info.chain_bone, get_ik_target_idx_for_slot_assignment_on_chain(current_obj, ik_target_info)) + "_target"
    # empty.empty_display_size = 0.4

    # If iktarget info is none, this is probably a sequence and this particular clip doesn't have it assigned.
    if ik_target_info.target_obj is None or ik_target_info.target_obj == "":
        return {"FINISHED"}
    if ik_target_info.target_obj not in bpy.data.objects:
        operator.report({'ERROR'}, "Target object not found.")
        return {'CANCELLED'}
    if ik_target_info.target_bone not in bpy.data.objects[ik_target_info.target_obj].pose.bones:
        operator.report({'ERROR'}, "Target bone not found.")
        return {'CANCELLED'}
    target_obj = bpy.data.objects[ik_target_info.target_obj]
    chain_bone = ik_target_info.chain_bone

    if chain_bone == "b__L_Hand__":
        final_bone = "L.Hand"
        blender_rig_ik_target_bone_name = current_obj.ik_bone_05_ik_name
    elif chain_bone == "b__R_Hand__":
        final_bone = "R.Hand"
        blender_rig_ik_target_bone_name = mirror_bone_name(current_obj.ik_bone_05_ik_name)
    elif chain_bone == "b__L_Foot__":
        final_bone = "L.Foot"
        blender_rig_ik_target_bone_name = current_obj.ik_bone_15_ik_name
    elif chain_bone == "b__R_Foot__":
        final_bone = "R.Foot"
        blender_rig_ik_target_bone_name = mirror_bone_name(current_obj.ik_bone_15_ik_name)
    elif chain_bone == "b__ROOT_bind__":
        final_bone = "RootBind"
        blender_rig_ik_target_bone_name = "b__ROOT_bind__"
    else:
        raise Exception("Bone not found")

    slot_assignment_idx = get_ik_target_idx_for_slot_assignment_on_chain(current_obj, ik_target_info)

    bone_name_target = "ik_bone_{}_{}".format(final_bone, slot_assignment_idx)
    bone_name_target_weight = "ik_bone_{}_{}_weight".format(final_bone, slot_assignment_idx)
    bpy.ops.object.mode_set(mode="POSE")
    constraint = create_childof_constraint_bone(current_obj, bpy.data.objects[ik_target_info.target_obj],
                                                current_obj.pose.bones[bone_name_target],
                                                ik_target_info.target_bone)
    loc_constraint = create_location_constraint(current_obj, bone_name_target,
                                                current_obj.pose.bones[blender_rig_ik_target_bone_name])

    rot_constraint = create_rotation_constraint_worldspace(current_obj, bone_name_target,
                                                           current_obj.pose.bones[blender_rig_ik_target_bone_name])

    # Slot assignment idx 0 is reserved for world space ik, aka IK targeting the root bone.
    # It should always be under the other bones and always be on
    if slot_assignment_idx != 0:
        add_driver(loc_constraint, current_obj, "influence",
                   "pose.bones[\"{}\"].location[2]".format(bone_name_target_weight))
        add_driver(rot_constraint, current_obj, "influence",
                   "pose.bones[\"{}\"].location[2]".format(bone_name_target_weight))

    bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.select_all(action='DESELECT')

    current_obj.select_set(True)
    return {"FINISHED"}
class OT_S4ANIMTOOLS_PreviewSlotAssignment(bpy.types.Operator):
    """Delete an ik target."""
    bl_idname = "s4animtools.preview_slot_assignment"
    bl_label = "Edit an IK Target"
    bl_options = {"REGISTER", "UNDO"}

    command: bpy.props.StringProperty()

    def execute(self, context):
        if not self.command.isdigit():
            return {'CANCELLED'}

        return preview_slot_assignment(self, context.object, int(self.command))


class OT_S4ANIMTOOLS_PreviewAllSlotAssignments(bpy.types.Operator):
    bl_idname = "s4animtools.preview_all_slot_assignments"
    bl_label = "Edit an IK Target"
    bl_options = {"REGISTER", "UNDO"}


    def execute(self, context):
        if context.object is None:
            self.report({'ERROR'}, "No selected object found.")
        for slot_assignment_idx in range(len(context.object.ik_targets)):
            preview_slot_assignment(self, context.object, slot_assignment_idx)
        return {"FINISHED"}


