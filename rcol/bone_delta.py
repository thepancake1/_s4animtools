from s4animtools import Float32, UInt32
from s4animtools.serialization import Serializable
from s4animtools.stream import StreamReader
from s4animtools.rcol.rcol_wrapper import RCOL
import bpy
from bpy_extras.io_utils import ImportHelper

class SlotAdjust(Serializable):
    def __init__(self):
        self.bone_hash = 0

        self.pos_x = 0
        self.pos_y = 0
        self.pos_z = 0

        self.scale_x = 0
        self.scale_y = 0
        self.scale_z = 0

        self.rot_x = 0
        self.rot_y = 0
        self.rot_z = 0
        self.rot_w = 0

    def read(self, reader:StreamReader):
        self.pos_x = reader.float32()
        self.pos_y = reader.float32()
        self.pos_z = reader.float32()
        self.scale_x = reader.float32()
        self.scale_y = reader.float32()
        self.scale_z = reader.float32()

        self.rot_x = reader.float32()
        self.rot_y = reader.float32()
        self.rot_z = reader.float32()
        self.rot_w = reader.float32()

        return self

    def serialize(self):
        data = [Float32(self.pos_x), Float32(self.pos_y), Float32(self.pos_z), Float32(self.scale_x),
                Float32(self.scale_y), Float32(self.scale_z),
                Float32(self.rot_x), Float32(self.rot_y), Float32(self.rot_z), Float32(self.rot_w)]

        serialized_stuff = []
        for value in data:
            serialied = value.serialize()
            serialized_stuff.append(serialied)
        return serialized_stuff
class BoneDelta(Serializable):
    def __init__(self, identifier=b""):
        self.version = 12
        self.bones = []


    @property
    def bone_count(self):
        return len(self.bones)

    def read(self, reader:StreamReader):
        self.version = reader.u32()
        bone_count = reader.u32()
        for bone in range(bone_count):
            self.bones.append(SlotAdjust().read(reader))

        return self
    def serialize(self):
        serialized_stuff = []
        data = [UInt32(self.version), UInt32(self.bone_count), *self.bones]
        for value in data:
            serialized_stuff.append(value.serialize())

        return serialized_stuff





if __name__ == "__main__":
    filepath = r"D:\Assets\Projects\Sims 3 Exporter\S3_0355E0A6_00000001_000000008114DDC7_amTopNudenormal%%+BOND.bonedelta"
    reader = StreamReader(filepath)
    rcol = RCOL().read(reader)
    bonedelta_chunk = None
    for chunk in rcol.chunk_data:
        print(rcol.chunk_data, type(chunk))
        import s4animtools.rcol.bone_delta

        #TODO wtf, why does BoneDelta on its own not work on this
        #print(chunk, isinstance(chunk, s4animtools.rcol.bone_delta.BoneDelta))

        if isinstance(chunk, s4animtools.rcol.bone_delta.BoneDelta):
            bonedelta_chunk = chunk
            break


    print(bonedelta_chunk.bones)