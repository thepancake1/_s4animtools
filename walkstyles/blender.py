import glob
import os

from bpy.props import IntProperty, CollectionProperty, FloatProperty, StringProperty
from bpy.types import PropertyGroup
from bpy_extras.io_utils import ImportHelper

import bpy

import xml.etree.ElementTree as ET

from s4animtools import get_32bit_hash


class S4ANIMTOOLS_OT_AddNewLocomotionBuilder(bpy.types.Operator):
    bl_idname = "s4animtools.add_new_locomotion_builder"
    bl_label = "Add New Locomotion Builder"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.scene.locomotion_builders.add()

        return {"FINISHED"}


class S4ANIMTOOLS_OT_ReadLocomotionBuilderFromFolderExtractedByS4S(bpy.types.Operator, ImportHelper):
    bl_idname = "s4animtools.read_locomotion_builder_from_folder"
    bl_label = "Read Locomotion Builder From Folder Extracted By S4S"
    bl_options = {"REGISTER", "UNDO"}

    def parse_variant(self, variant):
        for element in variant:
            if element.tag == "Builder":
                # Get the name of the locomotion builder
                locomotion_builder_stage_name = element.attrib.get("name", "")
                locomotion_builder_asset_name = element.attrib.get("asset_name", "")
                locomotion_builder = bpy.context.scene.locomotion_builders[-1]
                print(f"Adding Locomotion Builder: {locomotion_builder_stage_name} with asset name {locomotion_builder_asset_name}")
                setattr(locomotion_builder, locomotion_builder_stage_name, locomotion_builder_asset_name)
    def execute(self, context):
        context.scene.locomotion_builders.add()
        # Read the locomotion builder, allow the user to pick a file
        parent_paths_to_root = {}

        parent, root = self.parse_xml(self.filepath)
        parent_paths_to_root[self.filepath] = root
        i = 0
        while parent is not "" or i > 100:
            # Get 32 bit hash in hex str
            instance_string = "{:016X}".format(get_32bit_hash(parent))
            file_prefix = "27C01D95!00000000!"
            file_pattern = f"{file_prefix}{instance_string}.*"
            results = glob.glob(os.path.join(os.path.dirname(self.filepath), file_pattern))
            if results:
                parent, root = self.parse_xml(results[0])
                parent_paths_to_root[results[0]] = root
                parent = root.attrib.get("default_parent", "")
            i += 1

        for root in reversed(parent_paths_to_root.values()):
            for element in root:
                if element.tag == "Variant":
                    # Parse the variant and add it to the locomotion builder
                    self.parse_variant(element)

        return {"FINISHED"}

    def parse_xml(self, filepath):
        root = ET.parse(filepath).getroot()
        print(root.text, root.tag)
        parent = ""
        if root.tag == "Walkstyle":
            if root.attrib.get("default_parent", "") != "":
                parent = root.attrib.get("default_parent", "")
        return parent, root


def locomotion_register():
    bpy.utils.register_class(LocomotionBuilderVariantData)
    bpy.utils.register_class(S4ANIMTOOLS_OT_AddNewLocomotionBuilder)
    bpy.utils.register_class(S4ANIMTOOLS_OT_ReadLocomotionBuilderFromFolderExtractedByS4S)
    bpy.types.Scene.locomotion_builders = CollectionProperty(type=LocomotionBuilderVariantData)

def locomotion_unregister():
    bpy.utils.unregister_class(S4ANIMTOOLS_OT_AddNewLocomotionBuilder)
    bpy.utils.unregister_class(LocomotionBuilderVariantData)
    bpy.utils.unregister_class(S4ANIMTOOLS_OT_ReadLocomotionBuilderFromFolderExtractedByS4S)
    del bpy.types.Scene.locomotion_builders


class LocomotionBuilderVariantData(PropertyGroup):
    locomotion_builder_name: StringProperty()

    buildladder_up_start: StringProperty()
    buildladder_up_cycle_l: StringProperty()
    buildladder_up_cycle_r: StringProperty()
    buildladder_up_stop: StringProperty()
    buildladder_up_stop_l: StringProperty()
    buildladder_up_stop_r: StringProperty()

    buildladder_down_start: StringProperty()
    buildladder_down_start_l: StringProperty()
    buildladder_down_start_r: StringProperty()
    buildladder_down_cycle_l: StringProperty()
    buildladder_down_cycle_r: StringProperty()
    buildladder_down_stop: StringProperty()

    ladder_up_start: StringProperty()
    ladder_up_cycle_l: StringProperty()
    ladder_up_cycle_r: StringProperty()
    ladder_up_stop: StringProperty()

    ladder_down_start: StringProperty()
    ladder_down_cycle_l: StringProperty()
    ladder_down_cycle_r: StringProperty()
    ladder_down_stop: StringProperty()

    stairs_down_start: StringProperty()
    stairs_down_cycle: StringProperty()

    stairs_down_cycle_l: StringProperty()
    stairs_down_cycle_r: StringProperty()
    stairs_down_one_step: StringProperty()
    stairs_down_two_step: StringProperty()
    stairs_down_cycle_overlay: StringProperty()
    stairs_down_stop: StringProperty()

    stairs_up_start: StringProperty()
    stairs_up_cycle: StringProperty()
    stairs_up_cycle_l: StringProperty()
    stairs_up_cycle_r: StringProperty()
    stairs_up_one_step: StringProperty()
    stairs_up_two_step: StringProperty()
    stairs_up_cycle_overlay: StringProperty()
    stairs_up_stop: StringProperty()

    turn_to_path: StringProperty()

    cycle_step_down: StringProperty()
    backwards_cycle: StringProperty()

    cycle_step_up: StringProperty()
    cycle_step_up_l: StringProperty()
    cycle_step_up_r: StringProperty()

    cycle_step_down_l: StringProperty()
    cycle_step_down_r: StringProperty()
    step: StringProperty()
    backwards_start: StringProperty()

    start: StringProperty()
    turn: StringProperty()


    cycle: StringProperty()
    cycle_l: StringProperty()
    cycle_r: StringProperty()

    cycle_overlay: StringProperty()
    cycle_overlay_l: StringProperty()
    cycle_overlay_r: StringProperty()

    stop: StringProperty()
    stop_with_transition: StringProperty()
    backwards_stop: StringProperty()

    global_overlay: StringProperty()

def draw_locomotion_builder_data(layout, context):
    locomotion_builder: list[LocomotionBuilderVariantData] = context.scene.locomotion_builders
    column = layout.column()
    for locomotion_builder_item in locomotion_builder:
        column = layout.column()

        column.prop(locomotion_builder_item, "locomotion_builder_name", text="Locomotion Builder Name")
        for prop in LocomotionBuilderVariantData.bl_rna.properties:
            if prop.is_readonly:
                continue
            if prop.name != "locomotion_builder_name":
                if hasattr(locomotion_builder_item, prop.name):
                    if getattr(locomotion_builder_item, prop.name) != "":
                        column = column.column()
                        column.prop(locomotion_builder_item, prop.name, text=prop.name.replace("_", " ").title())