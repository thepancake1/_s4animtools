import math

from _s4animtools.rcol.skin import Skin
from _s4animtools.serialization.types.basic import UInt32, UInt64, Bytes
from _s4animtools.serialization import get_size


def get_combined_len(value):
    size = 0
    if isinstance(value, list):
        for item in value:
            size += len(item)
    else:
        return len(value)
    return size
class ChunkInfo:
    def __init__(self, chunk_position = 0, chunk_size = 0):
        self.chunk_position = chunk_position
        self.chunk_size = chunk_size

    def read(self, stream):
        self.chunk_position = UInt32.deserialize(stream.read(4))
        self.chunk_size = UInt32.deserialize(stream.read(4))
        return self

    def serialize(self):
        data = [UInt32(self.chunk_position), UInt32(self.chunk_size)]
        serialized_stuff = []
        for value in data:
            serialized_stuff.append(value.serialize())

        return serialized_stuff

    def __repr__(self):
        return "{}".format(vars(self))

class TGI:
    def __init__(self):
        self.i = 0
        self.t = 0
        self.g = 0

    def read(self, stream):
        self.i = UInt64.deserialize(stream.read(8))
        self.t = UInt32.deserialize(stream.read(4))
        self.g = UInt32.deserialize(stream.read(4))
        return self

    def serialize(self):
        data = [UInt64(self.i), UInt32(self.t), UInt32(self.g)]
        serialized_stuff = []
        for value in data:
            serialized_stuff.append(value.serialize())

        return serialized_stuff

    def __repr__(self):
        return "{}".format(vars(self))
class RCOL:
    def __init__(self):
        self.version = 0
        self.public_chunks = 0
        self.index3 = 0
        self.external_count = 0
        self.internal_count = 0
        self.internal_tgis = []
        self.external_tgis = []
        self.chunk_info = []
        self.chunk_data = []
    def read(self, stream):
        self.version = UInt32.deserialize(stream.read(4))
        self.public_chunks = UInt32.deserialize(stream.read(4))
        self.index3 = UInt32.deserialize(stream.read(4))
        self.external_count = UInt32.deserialize(stream.read(4))
        self.internal_count = UInt32.deserialize(stream.read(4))
        for i in range(self.internal_count):
            self.internal_tgis.append(TGI().read(stream))
        for i in range(self.external_count):
            self.external_tgis.append(TGI().read(stream))
        for i in range(self.internal_count):
            self.chunk_info.append(ChunkInfo().read(stream))
        for i in range(self.internal_count):
            stream.seek(self.chunk_info[i].chunk_position)
            data = stream.read(4)
            stream.seek(self.chunk_info[i].chunk_position)
            if "SKIN" in data.decode("ascii"):
                chunk_data = Skin().read(stream)
               # print(stream.tell())

            else:
                chunk_data = Bytes(stream.read(self.chunk_info[i].chunk_size))
            self.chunk_data.append(chunk_data)

        print(vars(self))

    def align_dword_boundaries(self, header_size):
        chunk_info_size = 8
        new_chunk_infos = []
        serialized_chunk_info = []
        serialized_body = []
        current_pos = header_size

        for i in range(self.internal_count):
            current_pos += chunk_info_size

        print(current_pos)


        for i in range(self.internal_count):
            print(current_pos)
           # if isinstance(self.chunk_data[i], Skin):
            current_pos = self.pad(current_pos, serialized_body)

            serialized_body.append(self.chunk_data[i].serialize())
            current_chunk_len = get_size(self.chunk_data[i].value)
            print(current_chunk_len, "chunklength")
            #print(self.chunk_data[i].value)
            new_chunk_infos.append(ChunkInfo(current_pos, current_chunk_len))
            current_pos += current_chunk_len


        for i in range(self.internal_count):
            serialized_chunk_info.append(new_chunk_infos[i].serialize())
        serialized = [*serialized_chunk_info, *serialized_body]
        return serialized

    def pad(self, current_pos, serialized_body):
        next_boundary = math.ceil(current_pos / 4) * 4
        print(current_pos, next_boundary)
        if current_pos % 4 != 0:
            print(current_pos)
            print("Chunk is not on DWORD boundary")
            delta_pos = next_boundary - current_pos
            print("Padding {} bytes".format(delta_pos))
            serialized_body.append(bytearray(delta_pos))
            current_pos += delta_pos
        return current_pos

    def sync_rig_to_mesh(self, vertex_groups):
        print("Syncing rig to mesh")
        for i in range(self.internal_count):
            if isinstance(self.chunk_data[i], Skin):
                self.chunk_data[i].matrices.clear()
                self.chunk_data[i].hashes.clear()
                self.chunk_data[i].count = len(vertex_groups)
                for v in range(len(vertex_groups)):

                    self.chunk_data[i].hashes.append(vertex_groups[v].name)

                for v in range(len(vertex_groups)):
                    flattened_matrix = vertex_groups[v].flattened_matrix
                    self.chunk_data[i].matrices.append(flattened_matrix)


    def serialize(self):
        data = [UInt32(self.version), UInt32(self.public_chunks), UInt32(self.index3), UInt32(self.external_count),
                UInt32(self.internal_count), *self.internal_tgis, *self.external_tgis]

        serialized_stuff = []
        total_len = 0
        for value in data:
            serialied = value.serialize()
            serialized_stuff.append(serialied)
            total_len += get_combined_len(serialied)
          #  print(total_len, serialied)
        #print(total_len)
        # Pad to next DWORD between chunks
        serialized_stuff.append(self.align_dword_boundaries(total_len))
        return serialized_stuff

if __name__ == "__main__":
    pass