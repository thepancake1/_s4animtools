import io
import os
import bpy
import _s4animtools.serialization

import _s4animtools.serialization
from _s4animtools.rcol.rcol_wrapper import RCOL
from _s4animtools.rig.create_rig import Rig
from _s4animtools.rcol.skin import VertexGroup
from _s4animtools.serialization.fnv import get_32bit_hash

class ExportRig(bpy.types.Operator):
    bl_idname = "s4animtools.export_rig"
    bl_label = "Export Rig"
    bl_options = {"REGISTER", "UNDO"}
    def execute(self, context):
        armature = bpy.context.object.data
        anim_path = os.path.join(os.environ["HOMEPATH"], "Desktop") + os.sep + "Animation Workspace"
        if not os.path.exists(anim_path):
            os.mkdir(anim_path)
        serialized_rig = Rig().create(armature.edit_bones[:])
        all_data = io.BytesIO()
        _s4animtools.serialization.recursive_write([*serialized_rig.serialize()], all_data)

        with open("{}\\{}".format(anim_path, "{}.RIG".format(bpy.context.object.name)), "wb") as file:
            file.write(all_data.getvalue())

    def invoke(self, context, event):

        # this is important, it will run the modal function
        # without this the operator would just execute and end
        self.execute(context)

        return {'FINISHED'}


class SyncRigToMesh(bpy.types.Operator):
    bl_idname = "s4animtools.sync_rig_to_mesh"
    bl_label = "Sync Rig To Mesh"
    bl_options = {"REGISTER", "UNDO"}



    def execute(self, context):
        return {"FINISHED"}
        rcol = RCOL()


        obj = bpy.context.object
        ready_vertex_groups = []
        for group in bpy.data.objects["Cube"].vertex_groups:
            print(group)
            group_name = group.name
            armature = obj.data
            bones = armature.edit_bones[:]
            hashed_name = get_32bit_hash(group_name)
            for bone in bones:
                if bone.name == group_name:
                   # print("{},{},{}".format(group_name, bone.name, hashed_name))
                    mat_values = []
                    parent_bone = bone.parent
                    bp1 = bone.matrix
                    #bp2 = parent_bone.matrix
                    bp3 = armature.edit_bones["b__ROOT__"].matrix
                    world_matrix = bpy.context.object.matrix_world
                    matrix_data = (bp3.inverted() @ bp1).inverted()
                    current_col = 0
                    current_idx = 0
                    for col in matrix_data:
                        if current_col >= 3:
                            break
                        for val in col:

                            mat_values.append(round(val, 4))
                            current_idx += 1
                        current_col += 1
                    ready_vertex_groups.append(VertexGroup(hashed_name, mat_values))
        rcol.sync_rig_to_mesh(ready_vertex_groups)
        all_data = io.BytesIO()
        _s4animtools.serialization.recursive_write([*rcol.serialize()], all_data)

    def invoke(self, context, event):
        self.execute(context)

        return {'FINISHED'}