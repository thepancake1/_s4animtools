from s4animtools import f32, u32
from s4animtools.serialization import Serializable
from s4animtools.stream import FileReader
from s4animtools.rcol.rcol_wrapper import RCOL
from s4animtools.serialization.fnv import get_64bithash, get_32bit_hash
from mathutils import Vector
import glob
import bpy
# Map of currently applied slots to the magnitude of their difference
winning_slot_adjusts = {}
for filepath in glob.glob(r"D:\Assets\Projects\animations 2\TS3 Fix Bed Sleep Stutter\BoneDeltas\*"):
    reader = FileReader(filepath)
    rcol = RCOL().from_binary(reader)
    bonedelta_chunk = None
    for chunk in rcol.chunk_data:
        print(rcol.chunk_data, type(chunk))
        import s4animtools.rcol.bone_delta

        #TODO wtf, why does BoneDelta on its own not work on this
        #print(chunk, isinstance(chunk, s4animtools.rcol.bone_delta.BoneDelta))

        if isinstance(chunk, s4animtools.rcol.bone_delta.BoneDelta):
            bonedelta_chunk = chunk
            break

    bone_hash_to_bone = {}
    for bone in bpy.context.active_object.pose.bones:
        bone_hash_to_bone[get_32bit_hash(bone.name)] = bone
    if bonedelta_chunk is None:
        pass
    else:
        for bone in bonedelta_chunk.bones:
            print(bone.bone_hash)
            rig_bone = bone_hash_to_bone[bone.bone_hash]
            if rig_bone is not None:
                location = Vector((bone.pos_x, bone.pos_y, bone.pos_z))
                current_location_magnitude = location.magnitude
                print(rig_bone.name, current_location_magnitude)
                if bone.bone_hash in winning_slot_adjusts:
                    current_winning_slot_adjust_magnitude = winning_slot_adjusts[bone.bone_hash]
                    if current_location_magnitude > current_winning_slot_adjust_magnitude:
                        winning_slot_adjusts[bone.bone_hash] = current_location_magnitude
                        rig_bone.location = location
                else:
                    winning_slot_adjusts[bone.bone_hash] = current_location_magnitude
                    rig_bone.location = location