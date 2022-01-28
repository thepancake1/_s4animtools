import os

from _s4animtools.serialization.fnv import get_32bit_hash
from _s4animtools.serialization.types.basic import UInt32, Float32, Bytes, Int32
import bpy
from _s4animtools.stream import StreamReader

class Bone:
    def __init__(self):
        self.position = []
        self.rotation = []
        self.scale = []
        self.bone_name_length = 0
        self.bone_name = b""
        self.mirrored_bone_idx = 0
        self.parent_idx = 0
        self.bone_hash = 0
        self.flags = 0
    def read(self, reader):
        self.position = [reader.float32(), reader.float32(), reader.float32()]
        self.rotation = [reader.float32(), reader.float32(), reader.float32(), reader.float32()]
        self.scale = [reader.float32(), reader.float32(), reader.float32()]
        self.bone_name_length = reader.u32()
        self.bone_name = reader.read_string(self.bone_name_length)
        self.mirrored_bone_idx = reader.u32()
        self.parent_idx = reader.s32()
        self.bone_hash = reader.u32()
        self.flags = reader.u32()
        print(self.bone_name, hex(self.bone_hash))
        return self


    def create(self, current_bone, parent_bone, parent_idx, current_idx):
        bp1 = current_bone.matrix
        bp2 = parent_bone.matrix
        matrix_data = (bp2.inverted() @ bp1)
        location = (bp2.inverted() @ bp1).to_translation()
        rotation = matrix_data.to_quaternion()

        self.position = [Float32(round(location.x, 4)), Float32(round(location.y, 4)),
                         Float32(round(location.z, 4))]
        self.rotation = [Float32(round(rotation.x, 4)), Float32(round(rotation.y, 4)), Float32(round(rotation.z, 4)),
                         Float32(round(rotation.w, 4))]

        self.scale = [Float32(1), Float32(1), Float32(1)]
        self.bone_name_length, self.bone_name = UInt32(len(current_bone.name)), \
                                                Bytes(current_bone.name.encode('ascii'))
        self.mirrored_bone_idx = Int32(current_idx)
        self.parent_idx = Int32(parent_idx)
        self.bone_hash = UInt32(get_32bit_hash(current_bone.name))
        self.flags = UInt32(Rig.determine_bone_type(current_bone.name))
        return self
    def serialize(self):
        serialized = [*self.position, *self.rotation, *self.scale, self.bone_name_length, self.bone_name,
                      self.mirrored_bone_idx, self.parent_idx, self.bone_hash, self.flags]

        serialized_stuff = []
        for value in serialized:
            print(value)
            serialized_stuff.append(value.serialize())

        return serialized_stuff


class Rig:
    typical_flags_for_bone_type = {"b__ROOT__": 32, "default": 37180}

    @staticmethod
    def determine_bone_type(bone_name):
        if bone_name in Rig.typical_flags_for_bone_type:
            return Rig.typical_flags_for_bone_type[bone_name]
        if "subroot" in bone_name:
            return Rig.typical_flags_for_bone_type["b__ROOT__"]
        return Rig.typical_flags_for_bone_type["default"]

    def __init__(self):
        self.major_version = 0
        self.minor_version = 0
        self.bone_count = 0
        self.bones = []

    def read(self, reader):
        self.major_version = reader.u32()
        if not self.major_version >= 3 and not self.major_version <= 4:
            raise ValueError("Invalid rig version.")
        self.minor_version =  reader.u32()
        if not self.major_version >= 1 and not self.major_version <= 2:
            raise ValueError("Invalid rig version.")
        self.bone_count = reader.u32()
        self.bones = []
        for i in range(self.bone_count):
            self.bones.append(Bone().read(reader))
        return self
    def create(self, bones):
        self.major_version = UInt32(3)
        self.minor_version = UInt32(1)
        self.bone_count = UInt32(len(bones))
        self.bones = []
        bone_to_idx = {}
        for i in range(len(bones)):
            bone_to_idx[bones[i].name] = i
        for i in range(len(bones)):
            current_bone = bones[i]
            try:
                parent_bone = current_bone.parent
                parent_bone_idx = bone_to_idx[current_bone.parent.name]
            except:
                parent_bone = current_bone
                parent_bone_idx = -1
            self.bones.append(Bone().create(current_bone, parent_bone, parent_bone_idx, i))
        self.rig_name_length = UInt32(0)
        return self

    def serialize(self):
        serialized = [self.major_version, self.minor_version, self.bone_count, *self.bones, self.rig_name_length]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.serialize())

        return serialized_stuff

def create_rig_with_context(filepath, context):
    import math
    from mathutils import Vector, Matrix, Quaternion
    reader = StreamReader(filepath)
    rig_resource = Rig().read(reader)
    rig_name = os.path.basename(filepath)
    armdata = bpy.data.armatures.new(rig_name)
    ob_new = bpy.data.objects.new(rig_name, armdata)
    ob_new.rotation_euler = (math.radians(90), 0, math.radians(180))
    bpy.context.scene.collection.objects.link(ob_new)
    # must be in edit mode to add bones
    context.view_layer.objects.active = ob_new
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    edit_bones = ob_new.data.edit_bones
    for bone in rig_resource.bones:
        if bone.parent_idx >= 0:
            print(bone.parent_idx)
            #print(bone.parent_idx)
            parent_matrix = edit_bones[bone.parent_idx].matrix
            parent = edit_bones[bone.parent_idx]
        else:
            parent_matrix = Quaternion((1, 0, 0, 0)).to_matrix().to_4x4()

            parent = None
        b = edit_bones.new(bone.bone_name)
        vec = Vector((float(bone.position[0]), float(bone.position[1]), float(bone.position[2])))

        mat_rot = Quaternion(
            (float(bone.rotation[3]), float(bone.rotation[0]), float(bone.rotation[1]), float(bone.rotation[2]))).to_matrix().to_4x4()
        # print(vec)
        current_mat = parent_matrix @ Matrix.Translation(vec) @ mat_rot
        # current_mat =  current_mat  @ parent_matrix
        b.head = Vector((0, 0, 0.01))
        b.tail = Vector((0, 0, 0))
        #print(parent_matrix, bone.bone_name)
        b.matrix = current_mat
        if parent is not None:
            b.parent = parent
    ob_new.show_in_front = True
    pose_bones = ob_new.pose.bones
    bpy.ops.object.mode_set(mode='POSE')

    for idx, bone in enumerate(rig_resource.bones):
        pose_bones[idx].mirrored_bone = pose_bones[bone.mirrored_bone_idx].name
        pose_bones[idx].bone_flags = bin(bone.flags)[2:].rjust(24,"0")


    bpy.ops.object.mode_set(mode='OBJECT')


    return ob_new