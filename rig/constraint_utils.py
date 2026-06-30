import math


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

def create_ik_constraint(src_obj, src_bone_name, to_bone, pole_bone_name, pole_angle=0):
    constraint = to_bone.constraints.new("IK")
    constraint.target = src_obj
    constraint.subtarget = src_bone_name
    constraint.name = "IK Chain Constraint"
    constraint.chain_count = 3
    constraint.pole_angle = math.radians(pole_angle)
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


def create_dampedtrack_constraint(src_obj, src_bone_name, to_bone, track_axis):
    if track_axis not in ("X", "Y", "Z"):
        raise Exception("Invalid track axis specified. Expected X, Y or Z but got some other one for some reason." )
    constraint = to_bone.constraints.new("DAMPED_TRACK")
    constraint.target = src_obj
    constraint.subtarget = src_bone_name
    constraint.track_axis = f"TRACK_{track_axis}"
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
