

OFFSET = -0.491

from bpy.types import Operator, Panel
from bpy_extras.io_utils import ImportHelper
import bpy
import bmesh
from mathutils import Vector, Quaternion, Matrix

from s4animtools.rig.constraint_utils import create_location_constraint, create_rotation_constraint, \
duplicate_bone, create_ik_constraint, add_driver, create_stretchto_constraint, create_dampedtrack_constraint
import math
import os.path

def mirror_bone_name(bone_name):
    if bone_name.startswith("L."):
        return bone_name.replace("L.", "R.")
    elif bone_name.startswith("R."):
        return bone_name.replace("R.", "L.")
    elif bone_name.startswith("L_"):
        return bone_name.replace("L_", "R_")
    elif bone_name.startswith("R_"):
        return bone_name.replace("R_", "L_")
    else:
        if bone_name.startswith("b__CAS_L_"):
            return bone_name.replace("b__CAS_L_", "b__CAS_R_")
        elif bone_name.startswith("b__CAS_R_"):
            return bone_name.replace("b__CAS_R_", "b__CAS_L_")
        elif bone_name.startswith("b__L_"):
            return bone_name.replace("b__L_", "b__R_")
        elif bone_name.startswith("b__R_"):
            return bone_name.replace("b__R_", "b__L_")
        else:
            return bone_name

def create_bone_collection(active_object, collection_name):
    if collection_name not in active_object.data.collections:
        collection = active_object.data.collections.new(collection_name)
    else:
        collection = active_object.data.collections[collection_name]
    return collection

class S4ANIMTOOLS_OT_CreateIKChain(Operator):
    bl_idname = "s4animtools.create_ik_chain"
    bl_label = "Copy User Transform"
    bl_options = {'REGISTER', 'UNDO'}
    to_build : bpy.props.StringProperty()
    def execute(self, context):
        active_object = context.object
        if active_object.type != 'ARMATURE':
            raise Exception("The active object is not an armature")




        bpy.ops.object.mode_set(mode='EDIT')
        # Get the bones we want to create an ik chain for



        if self.to_build == "Arms":
            original_bone_start_name = active_object.original_bone_01
            original_bone_middle_name = active_object.original_bone_02
            original_bone_end_name = active_object.original_bone_03
            original_pole_target_name = active_object.original_bone_04

            ik_bone_start_name = active_object.ik_bone_01_ik_name  # Upperarm
            ik_bone_middle_name = active_object.ik_bone_02_ik_name  # Forearm
            ik_bone_end_name = active_object.ik_bone_03_ik_name  # Hand
            ik_bone_holder_name = active_object.ik_bone_04_ik_name  # Hand Holder
            ik_bone_target_name = active_object.ik_bone_05_ik_name  # Hand Target

            fk_bone_start_name = active_object.ik_bone_01_fk_name  # Upperarm
            fk_bone_middle_name = active_object.ik_bone_02_fk_name  # Forearm
            fk_bone_end_name = active_object.ik_bone_03_fk_name  # Hand

            pole_target_name = active_object.ik_bone_06_ik_name  # Pole Target
            pole_indicator_name = active_object.ik_bone_07_ik_name  # Pole Indicator
            left_collection_name = "Left Arm"
            right_collection_name = "Right Arm"

        elif self.to_build == "Legs":

            original_bone_start_name = active_object.original_bone_11
            original_bone_middle_name = active_object.original_bone_12
            original_bone_end_name = active_object.original_bone_13
            original_pole_target_name = active_object.original_bone_14

            ik_bone_start_name = active_object.ik_bone_11_ik_name  # Thigh
            ik_bone_middle_name = active_object.ik_bone_12_ik_name  # Calf
            ik_bone_end_name = active_object.ik_bone_13_ik_name  # Foot
            ik_bone_holder_name = active_object.ik_bone_14_ik_name  # Foot Holder
            ik_bone_target_name = active_object.ik_bone_15_ik_name  # Foot Target

            fk_bone_start_name = active_object.ik_bone_11_fk_name  # Thigh
            fk_bone_middle_name = active_object.ik_bone_12_fk_name  # Calf
            fk_bone_end_name = active_object.ik_bone_13_fk_name  # Foot

            pole_target_name = active_object.ik_bone_16_ik_name  # Pole Target
            pole_indicator_name = active_object.ik_bone_17_ik_name  # Pole Indicator

            left_collection_name = "Left Leg"
            right_collection_name = "Right Leg"
        else:
            raise Exception("Invalid IK chain type")
        for item in [original_bone_start_name, original_bone_middle_name, original_bone_end_name,
                     ik_bone_start_name, ik_bone_middle_name, ik_bone_end_name, ik_bone_holder_name, ik_bone_target_name,
                        fk_bone_start_name, fk_bone_middle_name, fk_bone_end_name]:
            if item == "":
                raise Exception("You left one of the bone names blank")

        # Check if any of the bone names are duplicates
        # The curly braces are used to create a set, which removes duplicates
        if len({original_bone_start_name, original_bone_middle_name, original_bone_end_name, original_pole_target_name,
                ik_bone_start_name, ik_bone_middle_name, ik_bone_end_name, ik_bone_holder_name, ik_bone_target_name,
                fk_bone_start_name, fk_bone_middle_name, fk_bone_end_name, pole_target_name}) != 13:
            raise Exception("You have duplicate bone names")

        self.create_control_bones_for_limb(active_object, context, ik_bone_end_name, ik_bone_holder_name,
                                           ik_bone_middle_name, ik_bone_start_name, ik_bone_target_name,
                                           original_bone_end_name, original_bone_middle_name,
                                           original_bone_start_name, original_pole_target_name, fk_bone_start_name, fk_bone_middle_name,
                                           fk_bone_end_name, pole_target_name, pole_indicator_name,
                                           left_collection_name, self.to_build)
        bpy.context.view_layer.objects.active = active_object

        bpy.ops.object.mode_set(mode='EDIT')
        # Mirror from left side to right side
        self.create_control_bones_for_limb(active_object, context, mirror_bone_name(ik_bone_end_name),
                                           mirror_bone_name(ik_bone_holder_name),
                                           mirror_bone_name(ik_bone_middle_name), mirror_bone_name(ik_bone_start_name),
                                           mirror_bone_name(ik_bone_target_name),
                                           mirror_bone_name(original_bone_end_name), mirror_bone_name(original_bone_middle_name),
                                           mirror_bone_name(original_bone_start_name), mirror_bone_name(original_pole_target_name),
                                           mirror_bone_name(fk_bone_start_name), mirror_bone_name(fk_bone_middle_name),
                                           mirror_bone_name(fk_bone_end_name), mirror_bone_name(pole_target_name), mirror_bone_name(pole_indicator_name),
                                           right_collection_name,
                                           self.to_build)
        return {"FINISHED"}

    def create_control_bones_for_limb(self, active_object, context, ik_bone_end_name, ik_bone_holder_name,
                                      ik_bone_middle_name, ik_bone_start_name, ik_bone_target_name,
                                      original_bone_end_name, original_bone_middle_name, original_bone_start_name,
                                      orignal_pole_target_name,
                                      fk_bone_start_name, fk_bone_middle_name, fk_bone_end_name, pole_target_name,
                                      pole_indicator_name, collection_name,
                                      to_build):

        # Switch to edit mode and then create the matching IK bones
        # After creating the bones, create the copy constraint
        original_bone_start_instance = active_object.data.edit_bones[original_bone_start_name]
        duplicate_bone(active_object, original_bone_start_name, ik_bone_start_name,
                       parent_bone_name=original_bone_start_instance.parent.name)
        duplicate_bone(active_object, original_bone_middle_name, ik_bone_middle_name,
                       parent_bone_name=ik_bone_start_name)
        duplicate_bone(active_object, original_bone_middle_name, pole_indicator_name,
                       parent_bone_name=ik_bone_start_name)
        duplicate_bone(active_object, original_bone_end_name, ik_bone_end_name,
                       parent_bone_name=ik_bone_middle_name)
        duplicate_bone(active_object, original_bone_end_name, ik_bone_holder_name,
                       parent_bone_name=ik_bone_middle_name)
        duplicate_bone(active_object, original_bone_end_name, ik_bone_target_name, parent_bone_name=None)
        duplicate_bone(active_object, original_bone_start_name, fk_bone_start_name,
                       parent_bone_name=original_bone_start_instance.parent.name)
        duplicate_bone(active_object, original_bone_middle_name, fk_bone_middle_name,
                       parent_bone_name=fk_bone_start_name)
        duplicate_bone(active_object, original_bone_end_name, fk_bone_end_name,
                       parent_bone_name=fk_bone_middle_name)
        duplicate_bone(active_object, orignal_pole_target_name, pole_target_name,
                       parent_bone_name=None)


        bpy.ops.object.mode_set(mode='POSE')

        ik_bone_start_instance = active_object.pose.bones[ik_bone_start_name]
        ik_bone_middle_instance = active_object.pose.bones[ik_bone_middle_name]
        ik_bone_end_instance = active_object.pose.bones[ik_bone_end_name]
        ik_bone_holder_instance = active_object.pose.bones[ik_bone_holder_name]
        ik_bone_target_instance = active_object.pose.bones[ik_bone_target_name]
        original_bone_start_instance = active_object.pose.bones[original_bone_start_name]
        original_bone_middle_instance = active_object.pose.bones[original_bone_middle_name]
        original_bone_end_instance = active_object.pose.bones[original_bone_end_name]
        pole_target_instance = active_object.pose.bones[pole_target_name]
        pole_indicator_instance = active_object.pose.bones[pole_indicator_name]

        fk_bone_start_instance = active_object.pose.bones[fk_bone_start_name]
        fk_bone_middle_instance = active_object.pose.bones[fk_bone_middle_name]
        fk_bone_end_instance = active_object.pose.bones[fk_bone_end_name]

        # Drive the visual bones from the IK bones
        # Note that src bone is the FK bone, and to_bone is the IK bone
        # c1 = create_location_constraint(src_obj=active_object, src_bone=ik_bone_start_name, to_bone=original_bone_start_instance)
        c2 = create_rotation_constraint(src_obj=active_object, src_bone_name=ik_bone_start_name,
                                        to_bone=original_bone_start_instance)
        # c3 = create_location_constraint(src_obj=active_object, src_bone=ik_bone_middle_name, to_bone=original_bone_middle_instance)
        c4 = create_rotation_constraint(src_obj=active_object, src_bone_name=ik_bone_middle_name,
                                        to_bone=original_bone_middle_instance)
        # c5 = create_location_constraint(src_obj=active_object, src_bone=ik_bone_end_name, to_bone=original_bone_end_instance)
        c6 = create_rotation_constraint(src_obj=active_object, src_bone_name=ik_bone_end_name,
                                        to_bone=original_bone_end_instance)
        create_rotation_constraint(src_obj=active_object, src_bone_name=ik_bone_target_name,
                                   to_bone=ik_bone_end_instance)
        create_ik_constraint(src_obj=active_object, src_bone_name=ik_bone_target_name, to_bone=ik_bone_holder_instance,
                             pole_bone_name=pole_target_name)
        c7 = create_rotation_constraint(src_obj=active_object, src_bone_name=fk_bone_start_name,
                                        to_bone=original_bone_start_instance)
        c8 = create_rotation_constraint(src_obj=active_object, src_bone_name=fk_bone_middle_name,
                                        to_bone=original_bone_middle_instance)
        c9 = create_rotation_constraint(src_obj=active_object, src_bone_name=fk_bone_end_name,
                                        to_bone=original_bone_end_instance)
        create_stretchto_constraint(src_obj=active_object, src_bone_name=pole_target_name, to_bone=pole_indicator_instance)
        if to_build == "Arms":
            if ik_bone_start_name.startswith("L."):
                influence_variable_name = "left_arm_ik_enabled"
            elif ik_bone_start_name.startswith("R."):
                influence_variable_name = "right_arm_ik_enabled"
            else:
                raise Exception("Invalid bone name")
            #for constraint in [c2, c4, c6]:
            #    add_driver(constraint, active_object, "influence", influence_variable_name)
            for constraint in [c7, c8, c9]:
                add_driver(constraint, active_object, "influence", influence_variable_name, func="1-influence")
        elif to_build == "Legs":
            if ik_bone_start_name.startswith("L."):
                influence_variable_name = "left_leg_ik_enabled"
            elif ik_bone_start_name.startswith("R."):
                influence_variable_name = "right_leg_ik_enabled"
            else:
                raise Exception("Invalid bone name")
            #for constraint in [c2, c4, c6]:
            #    add_driver(constraint, active_object, "influence", influence_variable_name)
            for constraint in [c7, c8, c9]:
                add_driver(constraint, active_object, "influence", influence_variable_name, func="1-influence")
        load_gizmo(filepath=os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                       "gizmo_upperarm.obj"))
        load_gizmo(filepath=os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "gizmo_hand.obj"))
        load_gizmo(filepath=os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "gizmo_poleindicator.obj"))
        load_gizmo(filepath=os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "gizmo_pole.obj"))
        load_gizmo(filepath=os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "gizmo_thigh.obj"))

        if context.object.game_type == "TS4":
            if to_build == "Arms":
                active_object.pose.bones[fk_bone_start_name].custom_shape = bpy.data.objects["gizmo_upperarm"]
                active_object.pose.bones[fk_bone_start_name].custom_shape_scale_xyz = (1, 1, 1)
                active_object.pose.bones[fk_bone_start_name].color.palette = "THEME01"
                active_object.pose.bones[fk_bone_start_name].use_custom_shape_bone_size = False


                active_object.pose.bones[fk_bone_start_name].custom_shape_rotation_euler = (0, 0, math.radians(90))
                active_object.pose.bones[fk_bone_middle_name].custom_shape = bpy.data.objects["gizmo_upperarm"]
                active_object.pose.bones[fk_bone_middle_name].custom_shape_scale_xyz = (1, 1, 1)
                active_object.pose.bones[fk_bone_middle_name].color.palette = "THEME01"
                active_object.pose.bones[fk_bone_middle_name].use_custom_shape_bone_size = False

                active_object.pose.bones[fk_bone_middle_name].custom_shape_rotation_euler = (0, 0, math.radians(90))
                active_object.pose.bones[fk_bone_end_name].custom_shape = bpy.data.objects["gizmo_hand"]
                active_object.pose.bones[fk_bone_end_name].custom_shape_scale_xyz = (1, 1, 1)
                active_object.pose.bones[fk_bone_end_name].color.palette = "THEME01"
                active_object.pose.bones[fk_bone_end_name].use_custom_shape_bone_size = False

                active_object.pose.bones[fk_bone_end_name].custom_shape_rotation_euler = (0, 0, math.radians(90))
                active_object.pose.bones[ik_bone_target_name].custom_shape = bpy.data.objects["gizmo_hand"]
                active_object.pose.bones[ik_bone_target_name].custom_shape_scale_xyz = (1, 1, 1)
                active_object.pose.bones[ik_bone_target_name].use_custom_shape_bone_size = False

                active_object.pose.bones[ik_bone_target_name].color.palette = "THEME04"
                active_object.pose.bones[ik_bone_target_name].custom_shape_rotation_euler = (0, 0, math.radians(90))


                active_object.pose.bones[pole_target_name].custom_shape = bpy.data.objects["gizmo_pole"]
                active_object.pose.bones[pole_target_name].custom_shape_scale_xyz = (1, 1, 1)
                active_object.pose.bones[pole_target_name].use_custom_shape_bone_size = False

                active_object.pose.bones[pole_target_name].color.palette = "THEME10"
                active_object.pose.bones[pole_target_name].custom_shape_rotation_euler = (0, 0, math.radians(90))

                active_object.pose.bones[pole_indicator_name].custom_shape = bpy.data.objects["gizmo_poleindicator"]
                active_object.pose.bones[pole_indicator_name].custom_shape_scale_xyz = (1, 1, 1)
                active_object.pose.bones[pole_indicator_name].use_custom_shape_bone_size = False
                active_object.pose.bones[pole_indicator_name].color.palette = "THEME10"
                active_object.pose.bones[pole_indicator_name].custom_shape_rotation_euler = (0, math.radians(-90), 0)

            elif to_build == "Legs":
                active_object.pose.bones[fk_bone_start_name].custom_shape = bpy.data.objects["gizmo_thigh"]
                active_object.pose.bones[fk_bone_start_name].custom_shape_scale_xyz = (1, 1, 1)
                active_object.pose.bones[fk_bone_start_name].color.palette = "THEME01"
                active_object.pose.bones[fk_bone_start_name].use_custom_shape_bone_size = False

                active_object.pose.bones[fk_bone_start_name].custom_shape_rotation_euler = (0, 0, math.radians(90))
                active_object.pose.bones[fk_bone_middle_name].custom_shape = bpy.data.objects["gizmo_upperarm"]
                active_object.pose.bones[fk_bone_middle_name].custom_shape_scale_xyz = (1, 1, 1)
                active_object.pose.bones[fk_bone_middle_name].color.palette = "THEME01"
                active_object.pose.bones[fk_bone_middle_name].use_custom_shape_bone_size = False

                active_object.pose.bones[fk_bone_middle_name].custom_shape_rotation_euler = (0, 0, math.radians(90))
                active_object.pose.bones[fk_bone_end_name].custom_shape = bpy.data.objects["gizmo_hand"]
                active_object.pose.bones[fk_bone_end_name].custom_shape_scale_xyz = (1, 1, 1)
                active_object.pose.bones[fk_bone_end_name].color.palette = "THEME01"
                active_object.pose.bones[fk_bone_end_name].use_custom_shape_bone_size = False

                active_object.pose.bones[fk_bone_end_name].custom_shape_rotation_euler = (0, 0, math.radians(90))
                active_object.pose.bones[ik_bone_target_name].custom_shape = bpy.data.objects["gizmo_hand"]
                active_object.pose.bones[ik_bone_target_name].custom_shape_scale_xyz = (1, 1, 1)
                active_object.pose.bones[ik_bone_target_name].use_custom_shape_bone_size = False

                active_object.pose.bones[ik_bone_target_name].color.palette = "THEME04"
                active_object.pose.bones[ik_bone_target_name].custom_shape_rotation_euler = (0, 0, math.radians(90))

                active_object.pose.bones[pole_target_name].custom_shape = bpy.data.objects["gizmo_pole"]
                active_object.pose.bones[pole_target_name].custom_shape_scale_xyz = (1, 1, 1)

                active_object.pose.bones[pole_target_name].color.palette = "THEME10"
                active_object.pose.bones[pole_target_name].use_custom_shape_bone_size = False

                active_object.pose.bones[pole_target_name].custom_shape_rotation_euler = (0, 0, math.radians(90))

                active_object.pose.bones[pole_indicator_name].custom_shape = bpy.data.objects["gizmo_poleindicator"]
                active_object.pose.bones[pole_indicator_name].custom_shape_scale_xyz = (1, 1, 1)
                active_object.pose.bones[pole_indicator_name].use_custom_shape_bone_size = False
                active_object.pose.bones[pole_indicator_name].color.palette = "THEME10"
                active_object.pose.bones[pole_indicator_name].custom_shape_rotation_euler = (
                0, math.radians(-90), 0)


        elif context.scene.game == "TS3":
            active_object.pose.bones[fk_bone_start_name].custom_shape = bpy.data.objects["gizmo_upperarm"]
            active_object.pose.bones[fk_bone_start_name].custom_shape_scale_xyz = (100, 100, 100)
            active_object.pose.bones[fk_bone_start_name].color.palette = "THEME01"
            active_object.pose.bones[fk_bone_start_name].custom_shape_rotation_euler = (0, 0, math.radians(180))
            active_object.pose.bones[fk_bone_middle_name].custom_shape = bpy.data.objects["gizmo_upperarm"]
            active_object.pose.bones[fk_bone_middle_name].custom_shape_scale_xyz = (100, 100, 100)
            active_object.pose.bones[fk_bone_middle_name].color.palette = "THEME01"

            active_object.pose.bones[fk_bone_middle_name].custom_shape_rotation_euler = (0, 0, math.radians(180))
            active_object.pose.bones[fk_bone_end_name].custom_shape = bpy.data.objects["gizmo_hand"]
            active_object.pose.bones[fk_bone_end_name].custom_shape_scale_xyz = (100, 100, 100)
            active_object.pose.bones[fk_bone_end_name].color.palette = "THEME01"

            active_object.pose.bones[fk_bone_end_name].custom_shape_rotation_euler = (0, 0, math.radians(180))
            active_object.pose.bones[ik_bone_target_name].custom_shape = bpy.data.objects["gizmo_hand"]
            active_object.pose.bones[ik_bone_target_name].custom_shape_scale_xyz = (120, 120, 120)

            active_object.pose.bones[ik_bone_target_name].color.palette = "THEME04"
            active_object.pose.bones[ik_bone_target_name].custom_shape_rotation_euler = (0, 0, math.radians(180))

            active_object.pose.bones[pole_target_name].custom_shape = bpy.data.objects["gizmo_pole"]
            active_object.pose.bones[pole_target_name].custom_shape_scale_xyz = (1, 1, 1)

            active_object.pose.bones[pole_target_name].color.palette = "THEME10"
            active_object.pose.bones[pole_target_name].custom_shape_rotation_euler = (0, 0, math.radians(90))

            active_object.pose.bones[pole_indicator_name].custom_shape = bpy.data.objects["gizmo_poleindicator"]
            active_object.pose.bones[pole_indicator_name].custom_shape_scale_xyz = (1, 1, 1)
            active_object.pose.bones[pole_indicator_name].use_custom_shape_bone_size = False
            active_object.pose.bones[pole_indicator_name].color.palette = "THEME10"
            active_object.pose.bones[pole_indicator_name].custom_shape_rotation_euler = (0, math.radians(-90), 0)

        fk_collection_name = collection_name + " FK"
        ik_collection_name = collection_name + " IK"
        export_collection_name = collection_name + " Export"

        collection = create_bone_collection(active_object, ik_collection_name)
        collection.assign(ik_bone_start_instance.bone)
        collection.assign(ik_bone_middle_instance.bone)
        collection.assign(ik_bone_end_instance.bone)

        collection = create_bone_collection(active_object, fk_collection_name)
        collection.assign(fk_bone_start_instance.bone)
        collection.assign(fk_bone_middle_instance.bone)
        collection.assign(fk_bone_end_instance.bone)

        collection = create_bone_collection(active_object, export_collection_name)
        collection.assign(original_bone_start_instance.bone)
        collection.assign(original_bone_middle_instance.bone)
        collection.assign(original_bone_end_instance.bone)


def load_gizmo(filepath):
    # Load the object from the given file path
    obj_name = os.path.splitext(os.path.basename(filepath))[0]
    if obj_name in bpy.data.objects:
        return
    bpy.ops.wm.obj_import(filepath=filepath)
    bpy.data.objects[obj_name].hide_viewport = True
class S4ANIMTOOLS_OT_FKIKSwitch(Operator):
    bl_idname = "s4animtools.fk_to_ik_switch"
    bl_label = "FK/IK Switch"
    bl_options = {'REGISTER', 'UNDO'}

    to_build : bpy.props.StringProperty()
    def execute(self, context):
        active_object = context.object

        if active_object.type != 'ARMATURE':
            raise Exception("The active object is not an armature")
        if self.to_build == "LeftArm":
            bone1_fk_name = active_object.ik_bone_01_fk_name
            bone2_fk_name = active_object.ik_bone_02_fk_name
            bone3_fk_name = active_object.ik_bone_03_fk_name
            target_bone_ik_name = active_object.ik_bone_05_ik_name
            pole_target_ik_name = active_object.ik_bone_06_ik_name

            bone1_ik_name = active_object.ik_bone_01_ik_name
            bone2_ik_name = active_object.ik_bone_02_ik_name
            bone3_ik_name = active_object.ik_bone_03_ik_name

            offset_matrix = Matrix.Translation((0, OFFSET, 0))
            property_name = "left_arm_ik_enabled"

        elif self.to_build == "RightArm":
            bone1_fk_name = mirror_bone_name(active_object.ik_bone_01_fk_name)
            bone2_fk_name = mirror_bone_name(active_object.ik_bone_02_fk_name)
            bone3_fk_name = mirror_bone_name(active_object.ik_bone_03_fk_name)
            target_bone_ik_name = mirror_bone_name(active_object.ik_bone_05_ik_name)
            pole_target_ik_name = mirror_bone_name(active_object.ik_bone_06_ik_name)


            bone1_ik_name = mirror_bone_name(active_object.ik_bone_01_ik_name)
            bone2_ik_name = mirror_bone_name(active_object.ik_bone_02_ik_name)
            bone3_ik_name = mirror_bone_name(active_object.ik_bone_03_ik_name)


            offset_matrix = Matrix.Translation((0, OFFSET, 0))
            property_name = "right_arm_ik_enabled"

        elif self.to_build == "LeftLeg":
            bone1_fk_name = active_object.ik_bone_11_fk_name
            bone2_fk_name = active_object.ik_bone_12_fk_name
            bone3_fk_name = active_object.ik_bone_13_fk_name
            target_bone_ik_name = active_object.ik_bone_15_ik_name
            pole_target_ik_name = active_object.ik_bone_16_ik_name


            bone1_ik_name = active_object.ik_bone_11_ik_name
            bone2_ik_name = active_object.ik_bone_12_ik_name
            bone3_ik_name = active_object.ik_bone_13_ik_name


            offset_matrix = Matrix.Translation((0, -OFFSET, 0))
            property_name = "left_leg_ik_enabled"

        elif self.to_build == "RightLeg":
            bone1_fk_name = mirror_bone_name(active_object.ik_bone_11_fk_name)
            bone2_fk_name = mirror_bone_name(active_object.ik_bone_12_fk_name)
            bone3_fk_name = mirror_bone_name(active_object.ik_bone_13_fk_name)

            bone1_ik_name = mirror_bone_name(active_object.ik_bone_11_ik_name)
            bone2_ik_name = mirror_bone_name(active_object.ik_bone_12_ik_name)
            bone3_ik_name = mirror_bone_name(active_object.ik_bone_13_ik_name)

            target_bone_ik_name = mirror_bone_name(active_object.ik_bone_15_ik_name)
            pole_target_ik_name = mirror_bone_name(active_object.ik_bone_16_ik_name)
            offset_matrix = Matrix.Translation((0, -OFFSET, 0))
            property_name = "right_leg_ik_enabled"

        else:
            raise Exception("Invalid IK chain type")
        # Pancake's fk to ik switch

        bone2_instance = active_object.pose.bones[bone2_fk_name]

        pole_target_ik_instance = active_object.pose.bones[pole_target_ik_name]
        # Gotta get the forward direction in world space
        mat = bone2_instance.matrix.inverted() @ (bone2_instance.matrix @ offset_matrix)
        # Apply the offset translation to the forearm bone
        pole_target_ik_instance.matrix = bone2_instance.matrix @ mat
        pole_target_ik_instance.keyframe_insert(data_path="location", frame=bpy.context.scene.frame_current)

        # Copy the last bone in the ik chain to the ik target

        left_hand_bone_target_instance = active_object.pose.bones[target_bone_ik_name]
        left_hand_bone_target_instance.matrix = active_object.pose.bones[bone3_fk_name].matrix
        left_hand_bone_target_instance.keyframe_insert(data_path="location", frame=bpy.context.scene.frame_current)
        left_hand_bone_target_instance.keyframe_insert(data_path="rotation_euler", frame=bpy.context.scene.frame_current)
       #setattr(active_object, property_name, 1)
       #active_object.keyframe_insert(data_path=property_name, frame=bpy.context.scene.frame_current)
       #setattr(active_object.pose.bones[bone1_fk_name].bone, "hide", True)
       #active_object.pose.bones[bone1_fk_name].bone.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current)
       #setattr(active_object.pose.bones[bone2_fk_name].bone, "hide", True)
       #active_object.pose.bones[bone2_fk_name].bone.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current)
       #setattr(active_object.pose.bones[bone3_fk_name].bone, "hide", True)
       #active_object.pose.bones[bone3_fk_name].bone.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current)

       #setattr(active_object.pose.bones[bone1_ik_name].bone, "hide", False)
       #active_object.pose.bones[bone1_ik_name].bone.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current)
       #setattr(active_object.pose.bones[bone2_ik_name].bone, "hide", False)
       #active_object.pose.bones[bone2_ik_name].bone.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current)
       #setattr(active_object.pose.bones[bone3_ik_name].bone, "hide", False)
       #active_object.pose.bones[bone3_ik_name].bone.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current)

        return {"FINISHED"}
class S4ANIMTOOLS_OT_IKFKSwitch(Operator):
    bl_idname = "s4animtools.ik_to_fk_switch"
    bl_label = "IK/FK Switch"
    bl_options = {'REGISTER', 'UNDO'}
    to_build : bpy.props.StringProperty()
    def execute(self, context):
        active_object = context.object
        if active_object.type != 'ARMATURE':
            raise Exception("The active object is not an armature")
        if self.to_build == "LeftArm":
            bone1_fk_name = active_object.ik_bone_01_fk_name
            bone2_fk_name = active_object.ik_bone_02_fk_name
            bone3_fk_name = active_object.ik_bone_03_fk_name

            bone1_ik_name = active_object.ik_bone_01_ik_name
            bone2_ik_name = active_object.ik_bone_02_ik_name
            bone3_ik_name = active_object.ik_bone_03_ik_name
            property_name = "left_arm_ik_enabled"

        elif self.to_build == "RightArm":
            bone1_fk_name = mirror_bone_name(active_object.ik_bone_01_fk_name)
            bone2_fk_name = mirror_bone_name(active_object.ik_bone_02_fk_name)
            bone3_fk_name = mirror_bone_name(active_object.ik_bone_03_fk_name)

            bone1_ik_name = mirror_bone_name(active_object.ik_bone_01_ik_name)
            bone2_ik_name = mirror_bone_name(active_object.ik_bone_02_ik_name)
            bone3_ik_name = mirror_bone_name(active_object.ik_bone_03_ik_name)
            property_name = "right_arm_ik_enabled"

        elif self.to_build == "LeftLeg":
            bone1_fk_name = active_object.ik_bone_11_fk_name
            bone2_fk_name = active_object.ik_bone_12_fk_name
            bone3_fk_name = active_object.ik_bone_13_fk_name

            bone1_ik_name = active_object.ik_bone_11_ik_name
            bone2_ik_name = active_object.ik_bone_12_ik_name
            bone3_ik_name = active_object.ik_bone_13_ik_name
            property_name = "left_leg_ik_enabled"

        elif self.to_build == "RightLeg":
            bone1_fk_name = mirror_bone_name(active_object.ik_bone_11_fk_name)
            bone2_fk_name = mirror_bone_name(active_object.ik_bone_12_fk_name)
            bone3_fk_name = mirror_bone_name(active_object.ik_bone_13_fk_name)

            bone1_ik_name = mirror_bone_name(active_object.ik_bone_11_ik_name)
            bone2_ik_name = mirror_bone_name(active_object.ik_bone_12_ik_name)
            bone3_ik_name = mirror_bone_name(active_object.ik_bone_13_ik_name)
            property_name = "right_leg_ik_enabled"
        else:
            raise Exception("Invalid IK chain type")

        # Pancake's ik to fk switch
        bone1_fk_instance = active_object.pose.bones[bone1_fk_name]
        bone2_fk_instance = active_object.pose.bones[bone2_fk_name]
        bone3_fk_instance = active_object.pose.bones[bone3_fk_name]

        bone1_ik_instance = active_object.pose.bones[bone1_ik_name]
        bone2_ik_instance = active_object.pose.bones[bone2_ik_name]
        bone3_ik_instance = active_object.pose.bones[bone3_ik_name]

        bone1_fk_instance.matrix = bone1_ik_instance.matrix
        bone2_fk_instance.matrix = bone2_ik_instance.matrix
        bone3_fk_instance.matrix = bone3_ik_instance.matrix

        # Set x and y of middle joint to zeor and normalize



        bone1_fk_instance.location = Vector((0,0,0))
        bone2_fk_instance.location = Vector((0,0,0))
        bone3_fk_instance.location = Vector((0,0,0))


        bone1_fk_instance.keyframe_insert(data_path="rotation_euler", frame=bpy.context.scene.frame_current)
        bone2_fk_instance.keyframe_insert(data_path="rotation_euler", frame=bpy.context.scene.frame_current)
        bone3_fk_instance.keyframe_insert(data_path="rotation_euler", frame=bpy.context.scene.frame_current)

        bone2_fk_instance.rotation_euler.x = 0
        bone2_fk_instance.rotation_euler.y = 0


     #  setattr(active_object, property_name, 0)
     #  active_object.keyframe_insert(data_path=property_name, frame=bpy.context.scene.frame_current)

     #  setattr(active_object.pose.bones[bone1_fk_name].bone, "hide", False)
     #  active_object.pose.bones[bone1_fk_name].bone.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current)
     #  setattr(active_object.pose.bones[bone2_fk_name].bone, "hide", False)
     #  active_object.pose.bones[bone2_fk_name].bone.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current)
     #  setattr(active_object.pose.bones[bone3_fk_name].bone, "hide", False)
     #  active_object.pose.bones[bone3_fk_name].bone.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current)


     #  setattr(active_object.pose.bones[bone1_ik_name].bone, "hide", True)
     #  active_object.pose.bones[bone1_ik_name].bone.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current)
     #  setattr(active_object.pose.bones[bone2_ik_name].bone, "hide", True)
     #  active_object.pose.bones[bone2_ik_name].bone.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current)
     #  setattr(active_object.pose.bones[bone3_ik_name].bone, "hide", True)
     #  active_object.pose.bones[bone3_ik_name].bone.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current)

        return {"FINISHED"}


class S4ANIMTOOLS_OT_CreateBones(Operator):
    bl_idname = "s4animtools.create_bones"
    bl_label = "Create Bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active_object = context.object
        load_gizmo(filepath=os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "gizmo_rootbind.obj"))
        load_gizmo(filepath=os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "gizmo_hand.obj"))
        load_gizmo(filepath=os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "gizmo_eyelid.obj"))
        load_gizmo(filepath=os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "gizmo_finger.obj"))
        if active_object.type != 'ARMATURE':
            raise Exception("The active object is not an armature")
        rootbind_bone = "b__ROOT_bind__"
        spine0_bone_name = "b__Spine0__"
        spine1_bone_name = "b__Spine1__"
        spine2_bone_name = "b__Spine2__"
        pelvis_bone_name = "b__Pelvis__"
        left_clavicle_bone_name = "b__L_Clavicle__"
        right_clavicle_bone_name = "b__R_Clavicle__"
        if rootbind_bone not in active_object.data.bones:
            raise Exception("The armature does not have a root bind bone")
        if spine0_bone_name not in active_object.data.bones or spine1_bone_name not in active_object.data.bones or spine2_bone_name not in active_object.data.bones:
            raise Exception("The armature does not have a complete set of spine bones")
        if pelvis_bone_name not in active_object.data.bones:
            raise Exception("The armature does not have a pelvis bone")
        if left_clavicle_bone_name not in active_object.data.bones or right_clavicle_bone_name not in active_object.data.bones:
            raise Exception("The armature does not have a complete set of clavicle bones")

        bpy.context.view_layer.objects.active = active_object

        bpy.ops.object.mode_set(mode='EDIT')

        ts3_rig = context.scene.game_type == "TS3"
        ts4_rig = context.scene.game_type == "TS4"

        if ts3_rig:
            glasses_name = "b__Glasses__"
            left_eye_name = "b__LeftEye__"
            right_eye_name = mirror_bone_name(left_eye_name)
            left_uplid_name = "b__LeftUpLid__"
            right_uplid_name = mirror_bone_name(left_uplid_name)
            left_lolid_name = "b__LeftLoLid__"
            right_lolid_name = mirror_bone_name(left_lolid_name)
        if ts4_rig:
            glasses_name = "b__CAS_Glasses__"
            left_eye_name = "b__L_Eye__"
            right_eye_name = mirror_bone_name(left_eye_name)
            left_uplid_name = "b__L_UpLid__"
            right_uplid_name = mirror_bone_name(left_uplid_name)
            left_lolid_name = "b__L_LoLid__"
            right_lolid_name = mirror_bone_name(left_lolid_name)
        duplicate_bone(active_object, glasses_name, "C.EyeTarget.FK", "b__Head__")
        duplicate_bone(active_object, left_eye_name, "L.EyeTarget.FK", "C.EyeTarget.FK")
        duplicate_bone(active_object, right_eye_name, "R.EyeTarget.FK", "C.EyeTarget.FK")
        duplicate_bone(active_object, left_uplid_name, "L.UpLid.FK", "b__Head__")
        duplicate_bone(active_object, right_uplid_name, "R.UpLid.FK", "b__Head__")
        duplicate_bone(active_object, left_lolid_name, "L.LoLid.FK", "b__Head__")
        duplicate_bone(active_object, right_lolid_name, "R.LoLid.FK", "b__Head__")
        duplicate_bone(active_object, "b__L_Eye__", "L.EyeBaked",
                       parent_bone_name="b__CAS_L_EyeScale__")
        duplicate_bone(active_object, "b__R_Eye__", "R.EyeBaked",
                       parent_bone_name="b__CAS_R_EyeScale__")


        if active_object.data.edit_bones["L.UpLid.FK"].head[2] < active_object.data.edit_bones["R.UpLid.FK"].head[1]:
            active_object.data.edit_bones["C.EyeTarget.FK"].head[2] += 0.15
            active_object.data.edit_bones["L.EyeTarget.FK"].head[2] += 0.2
            active_object.data.edit_bones["R.EyeTarget.FK"].head[2] += 0.2
            active_object.data.edit_bones["C.EyeTarget.FK"].tail[2] += 0.15
            active_object.data.edit_bones["L.EyeTarget.FK"].tail[2] += 0.2
            active_object.data.edit_bones["R.EyeTarget.FK"].tail[2] += 0.2

            active_object.data.edit_bones["L.UpLid.FK"].head[2] += 0.2
            active_object.data.edit_bones["R.UpLid.FK"].head[2] += 0.2
            active_object.data.edit_bones["L.LoLid.FK"].head[2] += 0.2
            active_object.data.edit_bones["R.LoLid.FK"].head[2] += 0.2
            active_object.data.edit_bones["L.UpLid.FK"].tail[2] += 0.2
            active_object.data.edit_bones["R.UpLid.FK"].tail[2] += 0.2
            active_object.data.edit_bones["L.LoLid.FK"].tail[2] += 0.2
            active_object.data.edit_bones["R.LoLid.FK"].tail[2] += 0.2

        else:

            active_object.data.edit_bones["C.EyeTarget.FK"].head[1] -= 0.15
            active_object.data.edit_bones["L.EyeTarget.FK"].head[1] -= 0.2
            active_object.data.edit_bones["R.EyeTarget.FK"].head[1] -= 0.2
            active_object.data.edit_bones["C.EyeTarget.FK"].tail[1] -= 0.15
            active_object.data.edit_bones["L.EyeTarget.FK"].tail[1] -= 0.2
            active_object.data.edit_bones["R.EyeTarget.FK"].tail[1] -= 0.2

            active_object.data.edit_bones["L.UpLid.FK"].head[1] -= 0.2
            active_object.data.edit_bones["R.UpLid.FK"].head[1] -= 0.2
            active_object.data.edit_bones["L.LoLid.FK"].head[1] -= 0.2
            active_object.data.edit_bones["R.LoLid.FK"].head[1] -= 0.2
            active_object.data.edit_bones["L.UpLid.FK"].tail[1] -= 0.2
            active_object.data.edit_bones["R.UpLid.FK"].tail[1] -= 0.2
            active_object.data.edit_bones["L.LoLid.FK"].tail[1] -= 0.2
            active_object.data.edit_bones["R.LoLid.FK"].tail[1] -= 0.2

        duplicate_bone(active_object, "L.EyeTarget.FK", "L.EyeTargetBaked",
                       parent_bone_name="L.EyeBaked")
        duplicate_bone(active_object, "R.EyeTarget.FK", "R.EyeTargetBaked",
                       parent_bone_name="R.EyeBaked")


        duplicate_bone(active_object, left_uplid_name, "L.UpLidBaked",
                       parent_bone_name="b__CAS_L_EyeScale__")
        duplicate_bone(active_object, right_uplid_name, "R.UpLidBaked",
                       parent_bone_name="b__CAS_R_EyeScale__")

        duplicate_bone(active_object, left_lolid_name, "L.LoLidBaked",
                       parent_bone_name="b__CAS_L_EyeScale__")
        duplicate_bone(active_object, right_lolid_name, "R.LoLidBaked",
                       parent_bone_name="b__CAS_R_EyeScale__")

        duplicate_bone(active_object, "L.UpLid.FK", "L.UpLidTargetBaked", "L.UpLidBaked")
        duplicate_bone(active_object, "R.UpLid.FK", "R.UpLidTargetBaked", "R.UpLidBaked")
        duplicate_bone(active_object, "L.LoLid.FK", "L.LoLidTargetBaked", "L.LoLidBaked")
        duplicate_bone(active_object, "R.LoLid.FK", "R.LoLidTargetBaked", "R.LoLidBaked")



        bpy.ops.object.mode_set(mode='POSE')

        slot_collection = create_bone_collection(active_object, "Slots")
        left_hand_collection = create_bone_collection(active_object, "Left Hand")
        right_hand_collection = create_bone_collection(active_object, "Right Hand")
        for bone in active_object.pose.bones:
            if bone.name.endswith("_slot"):
                slot_collection.assign(bone.bone)

            try:
                if bone.name.endswith("_slot"):
                    pass
                elif bone.parent.name == "b__L_Hand__" or bone.parent.name == "b__R_Hand__":
                    self.create_finger_shape(bone, bone.parent.name == "b__L_Hand__", left_hand_collection, right_hand_collection, False)
                elif bone.parent.parent.name == "b__L_Hand__" or bone.parent.parent.name == "b__R_Hand__":
                    self.create_finger_shape(bone, bone.parent.parent.name == "b__L_Hand__", left_hand_collection, right_hand_collection, True)
                elif bone.parent.parent.parent.name == "b__L_Hand__" or bone.parent.parent.parent.name == "b__R_Hand__":
                    self.create_finger_shape(bone, bone.parent.parent.parent.name == "b__L_Hand__", left_hand_collection, right_hand_collection, True)
            except Exception:
                pass

        active_object.pose.bones[left_clavicle_bone_name].custom_shape = bpy.data.objects["gizmo_hand"]
        active_object.pose.bones[left_clavicle_bone_name].custom_shape_scale_xyz = (1, 2, 1)
        active_object.pose.bones[left_clavicle_bone_name].use_custom_shape_bone_size = False
        active_object.pose.bones[left_clavicle_bone_name].custom_shape_translation[0] = 0.07
        active_object.pose.bones[left_clavicle_bone_name].custom_shape_translation[1] = 0.1
        active_object.pose.bones[left_clavicle_bone_name].custom_shape_rotation_euler[1] = math.radians(90)
        active_object.pose.bones[left_clavicle_bone_name].color.palette = "THEME03"

        active_object.pose.bones[right_clavicle_bone_name].custom_shape = bpy.data.objects["gizmo_hand"]
        active_object.pose.bones[right_clavicle_bone_name].custom_shape_scale_xyz = (1,  2, 1)
        active_object.pose.bones[right_clavicle_bone_name].use_custom_shape_bone_size = False
        active_object.pose.bones[right_clavicle_bone_name].custom_shape_translation[0] = 0.07
        active_object.pose.bones[right_clavicle_bone_name].custom_shape_translation[1] = 0.1
        active_object.pose.bones[right_clavicle_bone_name].custom_shape_rotation_euler[1] = math.radians(90)
        active_object.pose.bones[right_clavicle_bone_name].color.palette = "THEME03"

        active_object.pose.bones["L.UpLid.FK"].custom_shape = bpy.data.objects["gizmo_eyelid"]
        active_object.pose.bones["L.UpLid.FK"].custom_shape_scale_xyz = (1, 1, 1)
        active_object.pose.bones["L.UpLid.FK"].use_custom_shape_bone_size = False
        active_object.pose.bones["L.UpLid.FK"].custom_shape_rotation_euler = (math.radians(-90), math.radians(-90), 0)

        active_object.pose.bones["L.UpLid.FK"].color.palette = "THEME03"

        active_object.pose.bones["R.UpLid.FK"].custom_shape = bpy.data.objects["gizmo_eyelid"]
        active_object.pose.bones["R.UpLid.FK"].custom_shape_scale_xyz = (1, 1, 1)
        active_object.pose.bones["R.UpLid.FK"].custom_shape_rotation_euler = (math.radians(-90), math.radians(-90), 0)
        active_object.pose.bones["R.UpLid.FK"].use_custom_shape_bone_size = False
        active_object.pose.bones["R.UpLid.FK"].color.palette = "THEME03"


        active_object.pose.bones["L.LoLid.FK"].custom_shape = bpy.data.objects["gizmo_eyelid"]
        active_object.pose.bones["L.LoLid.FK"].custom_shape_scale_xyz = (1, 1, 1)
        active_object.pose.bones["L.LoLid.FK"].use_custom_shape_bone_size = False
        active_object.pose.bones["L.LoLid.FK"].custom_shape_rotation_euler = (math.radians(-90), math.radians(-270), 0)

        active_object.pose.bones["L.LoLid.FK"].color.palette = "THEME03"

        active_object.pose.bones["R.LoLid.FK"].custom_shape = bpy.data.objects["gizmo_eyelid"]
        active_object.pose.bones["R.LoLid.FK"].custom_shape_scale_xyz = (1, 1, 1)
        active_object.pose.bones["R.LoLid.FK"].use_custom_shape_bone_size = False
        active_object.pose.bones["R.LoLid.FK"].custom_shape_rotation_euler = (math.radians(-90), math.radians(-270), 0)

        spine_rotation = 90 if context.scene.game_type == "TS4" else 0

        active_object.pose.bones["R.LoLid.FK"].color.palette = "THEME03"

        active_object.pose.bones[rootbind_bone].custom_shape = bpy.data.objects["gizmo_rootbind"]
        active_object.pose.bones[rootbind_bone].custom_shape_scale_xyz = (1, 1, 1)
        active_object.pose.bones[rootbind_bone].use_custom_shape_bone_size = False
        active_object.pose.bones[rootbind_bone].color.palette = "THEME03"
        active_object.pose.bones[rootbind_bone].custom_shape_rotation_euler = (math.radians(spine_rotation), math.radians(90), 0)

        active_object.pose.bones[spine0_bone_name].custom_shape = bpy.data.objects["gizmo_rootbind"]
        active_object.pose.bones[spine0_bone_name].custom_shape_scale_xyz = (1, 1, 1)
        active_object.pose.bones[spine0_bone_name].use_custom_shape_bone_size = False
        active_object.pose.bones[spine0_bone_name].color.palette = "THEME03"
        active_object.pose.bones[spine0_bone_name].custom_shape_rotation_euler = (math.radians(spine_rotation), math.radians(90), 0)

        active_object.pose.bones[spine1_bone_name].custom_shape = bpy.data.objects["gizmo_rootbind"]
        active_object.pose.bones[spine1_bone_name].custom_shape_scale_xyz = (1, 1, 1)
        active_object.pose.bones[spine1_bone_name].use_custom_shape_bone_size = False
        active_object.pose.bones[spine1_bone_name].color.palette = "THEME03"
        active_object.pose.bones[spine1_bone_name].custom_shape_rotation_euler = (math.radians(spine_rotation), math.radians(90), 0)

        active_object.pose.bones[spine2_bone_name].custom_shape = bpy.data.objects["gizmo_rootbind"]
        active_object.pose.bones[spine2_bone_name].custom_shape_scale_xyz = (1, 1, 1)
        active_object.pose.bones[spine2_bone_name].use_custom_shape_bone_size = False
        active_object.pose.bones[spine2_bone_name].color.palette = "THEME03"
        active_object.pose.bones[spine2_bone_name].custom_shape_rotation_euler = (math.radians(spine_rotation), math.radians(90), 0)

        active_object.pose.bones[pelvis_bone_name].custom_shape = bpy.data.objects["gizmo_rootbind"]
        active_object.pose.bones[pelvis_bone_name].custom_shape_scale_xyz = (1, 1,1)
        active_object.pose.bones[pelvis_bone_name].use_custom_shape_bone_size = False
        active_object.pose.bones[pelvis_bone_name].color.palette = "THEME03"
        active_object.pose.bones[pelvis_bone_name].custom_shape_rotation_euler = (
        math.radians(spine_rotation), math.radians(90), 0)

        active_object.pose.bones["L.EyeTarget.FK"].custom_shape = bpy.data.objects["gizmo_rootbind"]
        active_object.pose.bones["L.EyeTarget.FK"].custom_shape_scale_xyz = (0.08, 0.1, 0.1)
        active_object.pose.bones["L.EyeTarget.FK"].use_custom_shape_bone_size = False
        active_object.pose.bones["L.EyeTarget.FK"].color.palette = "THEME02"
        active_object.pose.bones["L.EyeTarget.FK"].custom_shape_rotation_euler = (
        math.radians(180), math.radians(0), 0)

        active_object.pose.bones["R.EyeTarget.FK"].custom_shape = bpy.data.objects["gizmo_rootbind"]
        active_object.pose.bones["R.EyeTarget.FK"].custom_shape_scale_xyz = (0.08, 0.1, 0.1)
        active_object.pose.bones["R.EyeTarget.FK"].use_custom_shape_bone_size = False
        active_object.pose.bones["R.EyeTarget.FK"].color.palette = "THEME02"
        active_object.pose.bones["R.EyeTarget.FK"].custom_shape_rotation_euler = (
        math.radians(180), math.radians(0), 0)
        active_object.pose.bones["L.EyeTarget.FK"].custom_shape = bpy.data.objects["gizmo_rootbind"]
        active_object.pose.bones["L.EyeTarget.FK"].custom_shape_scale_xyz = (0.08, 0.1, 0.1)
        active_object.pose.bones["L.EyeTarget.FK"].use_custom_shape_bone_size = False
        active_object.pose.bones["L.EyeTarget.FK"].color.palette = "THEME02"
        active_object.pose.bones["L.EyeTarget.FK"].custom_shape_rotation_euler = (
        math.radians(180), math.radians(0), 0)

        active_object.pose.bones["C.EyeTarget.FK"].custom_shape = bpy.data.objects["gizmo_rootbind"]
        active_object.pose.bones["C.EyeTarget.FK"].custom_shape_scale_xyz = (0.16, 0.2, 0.2)
        active_object.pose.bones["C.EyeTarget.FK"].use_custom_shape_bone_size = False
        active_object.pose.bones["C.EyeTarget.FK"].color.palette = "THEME02"
        active_object.pose.bones["C.EyeTarget.FK"].custom_shape_rotation_euler = (
        math.radians(180), math.radians(0), 0)
        create_dampedtrack_constraint(active_object, src_bone_name="L.EyeTarget.FK", to_bone=active_object.pose.bones[left_eye_name])
        create_dampedtrack_constraint(active_object, src_bone_name="R.EyeTarget.FK", to_bone=active_object.pose.bones[right_eye_name])

        create_dampedtrack_constraint(active_object, src_bone_name="L.UpLid.FK", to_bone=active_object.pose.bones[left_uplid_name])
        create_dampedtrack_constraint(active_object, src_bone_name="R.UpLid.FK", to_bone=active_object.pose.bones[right_uplid_name])
        create_dampedtrack_constraint(active_object, src_bone_name="L.LoLid.FK", to_bone=active_object.pose.bones[left_lolid_name])
        create_dampedtrack_constraint(active_object, src_bone_name="R.LoLid.FK", to_bone=active_object.pose.bones[right_lolid_name])
       # bpy.ops.object.mode_set(mode='OBJECT')

        create_dampedtrack_constraint(active_object, src_bone_name="L.EyeTarget.FK", to_bone=active_object.pose.bones[left_eye_name])
        constraint = create_location_constraint(active_object, "L.EyeTargetBaked", active_object.pose.bones["L.EyeTarget.FK"])
        add_driver(constraint, active_object, "influence", "baked_eye_animation_enabled", func="influence")
        constraint = create_location_constraint(active_object, "R.EyeTargetBaked", active_object.pose.bones["R.EyeTarget.FK"])
        add_driver(constraint, active_object, "influence", "baked_eye_animation_enabled", func="influence")

        constraint = create_location_constraint(active_object, "L.UpLidTargetBaked", active_object.pose.bones["L.UpLid.FK"])
        add_driver(constraint, active_object, "influence", "baked_eye_animation_enabled", func="influence")
        constraint = create_location_constraint(active_object, "L.LoLidTargetBaked", active_object.pose.bones["L.LoLid.FK"])
        add_driver(constraint, active_object, "influence", "baked_eye_animation_enabled", func="influence")

        constraint = create_location_constraint(active_object, "R.UpLidTargetBaked", active_object.pose.bones["R.UpLid.FK"])
        add_driver(constraint, active_object, "influence", "baked_eye_animation_enabled", func="influence")
        constraint = create_location_constraint(active_object, "R.LoLidTargetBaked", active_object.pose.bones["R.LoLid.FK"])
        add_driver(constraint, active_object, "influence", "baked_eye_animation_enabled", func="influence")

        bpy.ops.object.mode_set(mode='EDIT')

        ik_chain_bones = ["L.Hand", "R.Hand", "L.Foot", "R.Foot", "RootBind"]
        for chain_idx in range(5):
            for ik_target_idx in range(11):
                # Create an empty bone for each of the IK targets
                ik_bone_name = f"ik_bone_{ik_chain_bones[chain_idx]}_{ik_target_idx}"
                duplicate_bone(active_object, "b__ROOT__", ik_bone_name, parent_bone_name="b__ROOT__")
                ik_bone_name = f"ik_bone_{ik_chain_bones[chain_idx]}_{ik_target_idx}_weight"
                duplicate_bone(active_object, "b__ROOT__", ik_bone_name, parent_bone_name="b__ROOT__")
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"FINISHED"}

    def create_finger_shape(self, bone, left_bone, left_collection, right_collection, should_locK_axis):
        bone.custom_shape = bpy.data.objects["gizmo_finger"]
        bone.custom_shape_scale_xyz = (1, 1, 1)
        bone.use_custom_shape_bone_size = False
        bone.custom_shape_rotation_euler = (0, 0, 0)
        if left_bone:
            bone.color.palette = "THEME03"

            left_collection.assign(bone.bone)
        else:
            bone.color.palette = "THEME01"

            right_collection.assign(bone.bone)
        if should_locK_axis:
            bone.lock_rotation[0] = True
            bone.lock_rotation[1] = True

class S4ANIMTOOLS_OT_LoadPresetBoneConfig(bpy.types.Operator):
    bl_idname = "s4animtools.load_preset_bone_config"
    bl_label = "Load Preset Bone Config"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.object.original_bone_01 = "b__L_UpperArm__"
        context.object.original_bone_02 = "b__L_Forearm__"
        context.object.original_bone_03 = "b__L_Hand__"
        context.object.original_bone_04 = "b__L_ArmExportPole__"

        context.object.ik_bone_01_fk_name = "L.UpperArm.FK"
        context.object.ik_bone_02_fk_name = "L.Forearm.FK"
        context.object.ik_bone_03_fk_name = "L.Hand.FK"

        context.object.ik_bone_01_ik_name = "L.UpperArm.IK"
        context.object.ik_bone_02_ik_name = "L.Forearm.IK"
        context.object.ik_bone_03_ik_name = "L.Hand.IK"
        context.object.ik_bone_04_ik_name = "L.HandHolder.IK"
        context.object.ik_bone_05_ik_name = "L.HandTarget.IK"
        context.object.ik_bone_06_ik_name = "L.ArmPole.IK"
        context.object.ik_bone_07_ik_name = "L.ArmPoleIndicator.IK"

        context.object.original_bone_11 = "b__L_Thigh__"
        context.object.original_bone_12 = "b__L_Calf__"
        context.object.original_bone_13 = "b__L_Foot__"
        context.object.original_bone_14 = "b__L_LegExportPole__"

        context.object.ik_bone_11_fk_name = "L.Thigh.FK"
        context.object.ik_bone_12_fk_name = "L.Calf.FK"
        context.object.ik_bone_13_fk_name = "L.Foot.FK"

        context.object.ik_bone_11_ik_name = "L.Thigh.IK"
        context.object.ik_bone_12_ik_name = "L.Calf.IK"
        context.object.ik_bone_13_ik_name = "L.Foot.IK"
        context.object.ik_bone_14_ik_name = "L.FootHolder.IK"
        context.object.ik_bone_15_ik_name = "L.FootTarget.IK"
        context.object.ik_bone_16_ik_name = "L.LegPole.IK"
        context.object.ik_bone_17_ik_name = "L.LegPoleIndicator.IK"

        return {'FINISHED'}