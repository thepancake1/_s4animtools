import unittest
import bpy

from s4animtools.rig.create_rig import create_rig_with_context
from s4animtools.bone_names import human_bones

class TestS4AnimTools(unittest.TestCase):
    expected_rig_name = "8EAF13DE!00000000!D057FCC534C1BCBB.Rig.binary"

    def setUp(self):
        from s4animtools import register
        register()
    def tearDown(self):
        pass

    def test_rig_import(self):
        # Load the rig from the file
        create_rig_with_context("test_data\\8EAF13DE!00000000!D057FCC534C1BCBB.Rig.binary", bpy.context)
        # Check if the rig is loaded correctly
        self.assertTrue(self.expected_rig_name in bpy.data.objects, "Rig not found in the file")

        # Check if the rig has the expected bones
        rig = bpy.data.objects[self.expected_rig_name]
        expected_bones = human_bones
        for bone in expected_bones:
            self.assertIn(bone, rig.pose.bones, f"Bone {bone} not found in the rig")

    def test_clip_export(self):
        create_rig_with_context("test_data\\8EAF13DE!00000000!D057FCC534C1BCBB.Rig.binary", bpy.context)
        # Set up clip info
        clip_info = {
            "name": "a2o_thepancake1_test_clip",
            "end_frame": 10,
            "export_path": "test_data\\TestClip.anim"
        }

        obj = bpy.data.objects[self.expected_rig_name]
        obj.rig_name = "x"
        #Set scene clip info
        bpy.context.scene.clip_splits = str(clip_info["end_frame"])

        bpy.context.scene.clip_name = clip_info["name"]

        bpy.context.scene.s4animtools_export_path = clip_info["export_path"]
        bpy.ops.s4animtools.new_export_clip()


