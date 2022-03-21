import math
from _s4animtools.rcol.footprints import Footprint
from _s4animtools.serialization.types.tgi import TGI
from _s4animtools.rcol.skin import Skin
from _s4animtools.serialization.types.basic import UInt32, Bytes
from _s4animtools.serialization import get_size
from _s4animtools.stream import StreamReader
import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator
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
        self.chunk_position = stream.u32()
        self.chunk_size = stream.u32()
        return self

    def serialize(self):
        data = [UInt32(self.chunk_position), UInt32(self.chunk_size)]
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
        self.internal_tgis = []
        self.external_tgis = []
        self.chunk_info = []
        self.chunk_data = []

    @property
    def internal_count(self):
        return len(self.internal_tgis)

    @property
    def external_count(self):
        return len(self.external_tgis)

    def read(self, stream):
        self.version = stream.u32()
        self.public_chunks = stream.u32()
        self.index3 = stream.u32()
        external_count = stream.u32()
        internal_count = stream.u32()

        if internal_count > 1000 or external_count > 1000:
            print("Probably garbage or not an RCOL file. Bailing.")
            return self
        for i in range(internal_count):
            self.internal_tgis.append(TGI().read(stream))
        for i in range(external_count):
            self.external_tgis.append(TGI().read(stream))
        for i in range(self.internal_count):
            self.chunk_info.append(ChunkInfo().read(stream))
        for i in range(self.internal_count):
            stream.seek(self.chunk_info[i].chunk_position)
            data = stream.u32(raw=True)
            stream.seek(self.chunk_info[i].chunk_position)
            tag = data.decode("ascii")
            if "SKIN" in tag:
                chunk_data = Skin().read(stream)
               # print(stream.tell())
            elif "FTPT" in tag:
                chunk_data = Footprint().read(stream)

            else:
                chunk_data = Bytes(stream.read(self.chunk_info[i].chunk_size))
            self.chunk_data.append(chunk_data)
        return self

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

class OT_S4ANIMTOOLS_ImportFootprint(bpy.types.Operator, ImportHelper):
    bl_idname = "s4animtools.import_footprint"
    bl_label = "Import Footprint"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        armature = bpy.context.object.data
        reader = StreamReader(self.filepath)
        print(self.filepath)
        rcol = RCOL().read(reader)
        footprint_chunk = None
        for chunk in rcol.chunk_data:
            if isinstance(chunk, Footprint):
                footprint_chunk = chunk
                break

        footprint_areas = footprint_chunk.footprint_areas

        for footprint_area in footprint_areas:
            vertices = []
            edges = []
            faces = []
            footprint_obj_name = hex(footprint_area.name_hash) + " Footprint"
            me = bpy.data.meshes.new(footprint_obj_name)
            ob = bpy.data.objects.new(footprint_obj_name, me)
            point_count = len(footprint_area.points)
            bounding_box = footprint_area.bounding_box
            max_y = bounding_box.max_y
            for idx, point in enumerate(footprint_area.points):
                vertices.append((point.x, -point.z, 0))
                if idx < point_count - 1:
                    edges.append((idx, idx+1))
                else:
                    edges.append((idx, 0))

            for idx in range(0, point_count-3, 3):
                faces.append((idx, idx+1, idx+2))
            if point_count != idx:
                faces.append((point_count-1, 0, point_count-2))

            me.from_pydata(vertices, [], faces)
            ob.show_name = True
            me.update()
            bpy.context.collection.objects.link(ob)
            ob.location.z = 
           #bpy.ops.object.select_all(action='DESELECT')
           #ob.select_set(True)
           #bpy.context.view_layer.objects.active = ob
           #bpy.ops.object.mode_set(mode='EDIT')

           #bpy.ops.mesh.select_all(action='SELECT')

           #bpy.ops.mesh.normals_make_consistent(inside=False)
           #bpy.ops.object.mode_set(mode='OBJECT')

        return {"FINISHED"}


if __name__ == "__main__":
    pass