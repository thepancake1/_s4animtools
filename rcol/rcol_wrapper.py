import io
import math
import os
import traceback
import s4animtools

from s4animtools.rcol.footprints import Footprint, Area, Point
from s4animtools.serialization.types.tgi import TGI
from s4animtools.rcol.skin import Skin
from s4animtools.serialization.types.basic import UInt32, Bytes
from s4animtools.serialization import get_size
from s4animtools.stream import StreamReader
import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator
from math import radians
from mathutils import Vector
import bmesh
from s4animtools.serialization.fnv import get_64bithash, get_32bit_hash, hash_name_or_get_hash, hash_name_or_get_hash_64

from math import pi


def get_combined_len(value):
    size = 0
    if isinstance(value, list):
        for item in value:
            size += len(item)
    else:
        return len(value)
    return size


class ChunkInfo:
    def __init__(self, chunk_position=0, chunk_size=0):
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
        self.version = 3
        self.public_chunks = 1
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
        print(self.version, self.public_chunks, self.index3)
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
                print(hex(self.internal_tgis[i].t))
                if self.internal_tgis[i].t == 0x355E0A6:
                    from s4animtools.rcol.bone_delta import BoneDelta
                    chunk_data = BoneDelta().read(stream)

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
            # print(self.chunk_data[i].value)
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

    def change_chunk_position_size(self, chunk_idx, position, size):
        chunk_info = self.chunk_info[chunk_idx]
        chunk_info.chunk_position = position
        chunk_info.chunk_size = size

    def update_chunk_position_size_automatically(self, chunk_idx):
        offset = self.serialize_to_get_current_offset(chunk_idx)
        self.change_chunk_position_size(chunk_idx, self.serialize_to_get_current_offset(chunk_idx),
                                        get_size(self.chunk_data[chunk_idx].value))

    def serialize_to_get_current_offset(self, chunk_idx):
        data = [UInt32(self.version), UInt32(self.public_chunks), UInt32(self.index3), UInt32(self.external_count),
                UInt32(self.internal_count), *self.internal_tgis, *self.external_tgis, *self.chunk_info,
                *self.chunk_data[:chunk_idx - 1]]

        serialized_stuff = []
        total_len = 0
        for value in data:
            serialied = value.serialize()
            serialized_stuff.append(serialied)
            total_len += get_combined_len(serialied)
        # Pad to next DWORD between chunks
        return total_len

    def serialize(self):
        data = [UInt32(self.version), UInt32(self.public_chunks), UInt32(self.index3), UInt32(self.external_count),
                UInt32(self.internal_count), *self.internal_tgis, *self.external_tgis, *self.chunk_info,
                *self.chunk_data]

        serialized_stuff = []
        total_len = 0
        for value in data:
            serialied = value.serialize()
            serialized_stuff.append(serialied)
        #  print(total_len, serialied)
        # print(total_len)
        # Pad to next DWORD between chunks
        # serialized_stuff.append(self.align_dword_boundaries(total_len))
        return serialized_stuff


class ImportFootprint:
    def setup_properties(self, obj, footprint, is_routing_footprint, context):
        obj.is_footprint = True
        obj.show_footprint_options = True
        obj.for_placement = footprint.area_type_flags.for_placement
        obj.for_pathing = footprint.area_type_flags.for_pathing
        obj.is_enabled = footprint.area_type_flags.is_enabled
        obj.discouraged = footprint.area_type_flags.discouraged
        obj.landing_strip = footprint.area_type_flags.landing_strip
        obj.no_raycast = footprint.area_type_flags.no_raycast
        obj.placement_slotted = footprint.area_type_flags.placement_slotted
        obj.encouraged = footprint.area_type_flags.encouraged
        obj.terrain_cutout = footprint.area_type_flags.terrain_cutout

        obj.is_none = footprint.intersection_object_type.none
        obj.is_walls = footprint.intersection_object_type.walls
        obj.is_objects = footprint.intersection_object_type.objects
        obj.is_sims = footprint.intersection_object_type.sims
        obj.is_roofs = footprint.intersection_object_type.roofs
        obj.is_fences = footprint.intersection_object_type.fences
        obj.is_modular_stairs = footprint.intersection_object_type.modular_stairs
        obj.is_objects_of_same_type = footprint.intersection_object_type.objects_of_same_type
        obj.is_columns = footprint.intersection_object_type.columns
        obj.is_reserved_space = footprint.intersection_object_type.reserved_space
        obj.is_foundations = footprint.intersection_object_type.foundations
        obj.is_fenestration_node = footprint.intersection_object_type.fenestration_node
        obj.is_trim = footprint.intersection_object_type.trim

        obj.ignores_none = footprint.allow_intersection_types.none
        obj.ignores_walls = footprint.allow_intersection_types.walls
        obj.ignores_objects = footprint.allow_intersection_types.objects
        obj.ignores_sims = footprint.allow_intersection_types.sims
        obj.ignores_roofs = footprint.allow_intersection_types.roofs
        obj.ignores_fences = footprint.allow_intersection_types.fences
        obj.ignores_modular_stairs = footprint.allow_intersection_types.modular_stairs
        obj.ignores_objects_of_same_type = footprint.allow_intersection_types.objects_of_same_type
        obj.ignores_columns = footprint.allow_intersection_types.columns

        obj.ignores_reserved_space = footprint.allow_intersection_types.reserved_space
        obj.ignores_foundations = footprint.allow_intersection_types.foundations
        obj.ignores_fenestration_node = footprint.allow_intersection_types.fenestration_node
        obj.ignores_trim = footprint.allow_intersection_types.trim

        obj.terrain = footprint.surface_type_flags.terrain
        obj.floor = footprint.surface_type_flags.floor
        obj.pool = footprint.surface_type_flags.pool
        obj.pond = footprint.surface_type_flags.pond
        obj.fence_post = footprint.surface_type_flags.fence_post
        obj.any_surface = footprint.surface_type_flags.any_surface
        obj.air = footprint.surface_type_flags.air
        obj.roof = footprint.surface_type_flags.roof

        obj.slope = footprint.surface_attribute_flags.slope
        obj.outside = footprint.surface_attribute_flags.outside
        obj.inside = footprint.surface_attribute_flags.inside
        # Not an actual property, just for determining whether this goes in the first or second list in the footprint file
        obj.is_routing_footprint = is_routing_footprint

    def execute(self, context, filepath):
        reader = StreamReader(filepath)
        rcol = RCOL().read(reader)
        footprint_chunk = None
        for chunk in rcol.chunk_data:
            if isinstance(chunk, Footprint):
                footprint_chunk = chunk
                break

        footprint_areas = [*footprint_chunk.footprint_areas, *footprint_chunk.routing_areas]

        for footprint_area in footprint_areas:
            is_routing_area = footprint_area in footprint_chunk.routing_areas
            vertices = []
            edges = []
            faces = []
            footprint_obj_name = hex(footprint_area.name_hash) + " Footprint"
            me = bpy.data.meshes.new(footprint_obj_name)
            ob = bpy.data.objects.new(footprint_obj_name, me)
            point_count = len(footprint_area.points)
            bounding_box = footprint_area.bounding_box
            print(bounding_box.min_x, bounding_box.max_x, bounding_box.min_y, bounding_box.max_y, bounding_box.min_z,
                  bounding_box.max_z)
            min_y, max_y = bounding_box.min_y, bounding_box.max_y
            for idx, point in enumerate(footprint_area.points):
                vertices.append((point.x, -point.z, 0))
                if idx < point_count - 1:
                    edges.append((idx, idx + 1))
                else:
                    edges.append((idx, 0))

            # for idx in range(0, point_count-3, 3):
            #    faces.append((idx, idx+1, idx+2))
            # if point_count != idx:
            #  faces.append((point_count-1, 0, point_count-2))
            faces.append(list(range(0, point_count)))
            me.from_pydata(vertices, [], faces)
            ob.show_name = True
            me.update()
            bpy.context.collection.objects.link(ob)
            ob.location.z = min_y
            bpy.ops.object.select_all(action='DESELECT')
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            down = Vector((0, 0, -1))
            test_angle = radians(89)
            faces = [f for f in me.polygons
                     if f.normal.angle(down) < test_angle]
            bpy.ops.object.mode_set(mode='EDIT')

            if len(faces) > 0:
                bpy.ops.mesh.flip_normals()
            bpy.ops.object.mode_set(mode='OBJECT')

            bpy.ops.object.modifier_add(type='SOLIDIFY')
            bpy.context.object.modifiers["Solidify"].thickness = abs(max_y - min_y)
            bpy.context.object.modifiers["Solidify"].offset = 1
            bpy.context.object.modifiers["Solidify"].use_even_offset = True
            bpy.context.object.modifiers["Solidify"].use_quality_normals = True
            bpy.context.object.modifiers["Solidify"].use_rim = True
            self.setup_properties(ob, footprint_area, is_routing_area, context)
        # bpy.ops.object.select_all(action='DESELECT')
        # ob.select_set(True)
        # bpy.context.view_layer.objects.active = ob
        # bpy.ops.object.mode_set(mode='EDIT')

        # bpy.ops.mesh.select_all(action='SELECT')

        # bpy.ops.mesh.normals_make_consistent(inside=False)
        # bpy.ops.object.mode_set(mode='OBJECT')

        return {"FINISHED"}


class OT_S4ANIMTOOLS_ImportFootprint(bpy.types.Operator, ImportHelper):
    bl_idname = "s4animtools.import_footprint"
    bl_label = "Import Footprint"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context, filepath=None):
        return ImportFootprint().execute(context, self.filepath)


class OT_S4ANIMTOOLS_ExportFootprint(bpy.types.Operator):
    bl_idname = "s4animtools.export_footprint"
    bl_label = "Export Footprint"
    bl_options = {"REGISTER", "UNDO"}

    def get_bounding_box_points(self, points):
        min_x, max_x, min_z, max_z = 999, -999, 999, -999

        for point in points:
            if point[0] < min_x:
                min_x = point[0]
            if point[0] > max_x:
                max_x = point[0]

            if point[1] < min_z:
                min_z = point[1]
            if point[1] > max_z:
                max_z = point[1]
        return min_x, max_x, min_z, max_z

    def create_area(self, obj, footprint, points, context):
        # Should really set a property on the object instead of relying on name
        footprint.name_hash = hash_name_or_get_hash(obj.name.split(" ")[0]).value
        footprint.area_type_flags.for_placement = obj.for_placement
        footprint.area_type_flags.for_pathing = obj.for_pathing
        footprint.area_type_flags.is_enabled = obj.is_enabled
        footprint.area_type_flags.discouraged = obj.discouraged
        footprint.area_type_flags.landing_strip = obj.landing_strip
        footprint.area_type_flags.no_raycast = obj.no_raycast
        footprint.area_type_flags.placement_slotted = obj.placement_slotted
        footprint.area_type_flags.encouraged = obj.encouraged
        footprint.area_type_flags.terrain_cutout = obj.terrain_cutout

        footprint.intersection_object_type.none = obj.is_none
        footprint.intersection_object_type.walls = obj.is_walls
        footprint.intersection_object_type.objects = obj.is_objects
        footprint.intersection_object_type.sims = obj.is_sims
        footprint.intersection_object_type.roofs = obj.is_roofs
        footprint.intersection_object_type.fences = obj.is_fences
        footprint.intersection_object_type.modular_stairs = obj.is_modular_stairs
        footprint.intersection_object_type.objects_of_same_type = obj.is_objects_of_same_type
        footprint.intersection_object_type.columns = obj.is_columns
        footprint.intersection_object_type.reserved_space = obj.is_reserved_space
        footprint.intersection_object_type.foundations = obj.is_foundations
        footprint.intersection_object_type.fenestration_node = obj.is_fenestration_node
        footprint.intersection_object_type.trim = obj.is_trim

        footprint.allow_intersection_types.none = obj.ignores_none
        footprint.allow_intersection_types.walls = obj.ignores_walls
        footprint.allow_intersection_types.objects = obj.ignores_objects
        footprint.allow_intersection_types.sims = obj.ignores_sims
        footprint.allow_intersection_types.roofs = obj.ignores_roofs
        footprint.allow_intersection_types.fences = obj.ignores_fences
        footprint.allow_intersection_types.modular_stairs = obj.ignores_modular_stairs
        footprint.allow_intersection_types.objects_of_same_type = obj.ignores_objects_of_same_type
        footprint.allow_intersection_types.columns = obj.ignores_columns
        footprint.allow_intersection_types.reserved_space = obj.ignores_reserved_space
        footprint.allow_intersection_types.foundations = obj.ignores_foundations
        footprint.allow_intersection_types.fenestration_node = obj.ignores_fenestration_node
        footprint.allow_intersection_types.trim = obj.ignores_trim

        footprint.surface_type_flags.terrain = obj.terrain
        footprint.surface_type_flags.floor = obj.floor
        footprint.surface_type_flags.pool = obj.pool
        footprint.surface_type_flags.pond = obj.pond
        footprint.surface_type_flags.fence_post = obj.fence_post
        footprint.surface_type_flags.any_surface = obj.any_surface
        footprint.surface_type_flags.air = obj.air
        footprint.surface_type_flags.roof = obj.roof

        footprint.surface_attribute_flags.slope = obj.slope
        footprint.surface_attribute_flags.outside = obj.outside
        footprint.surface_attribute_flags.inside = obj.inside

        for point in points:
            new_point = Point()
            new_point.x = point[0]
            new_point.z = point[1]
            footprint.points.append(new_point)
        footprint.bounding_box.min_y, footprint.bounding_box.max_y = obj.location.z, obj.location.z + obj.dimensions.z

        footprint.bounding_box.min_x, footprint.bounding_box.max_x, footprint.bounding_box.min_z, footprint.bounding_box.max_z = self.get_bounding_box_points(
            points)

    def execute(self, context):

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        min_height = 9999
        max_height = -999
        valid_instance_ids = []
        valid_objs = []
        for obj in bpy.data.objects:
            if obj.is_footprint:

                valid_objs.append(obj)
                instance_id = hash_name_or_get_hash_64(obj.footprint_name)
                if instance_id not in valid_instance_ids:
                    valid_instance_ids.append(instance_id)
        for instance_id in valid_instance_ids:
            rcol = RCOL()
            footprint_chunk = Footprint()
            rcol.chunk_data.append(footprint_chunk)
            rcol.chunk_info.append(ChunkInfo(0, 0))
            new_tgi = TGI()
            new_tgi.t, new_tgi.g, new_tgi.i = 0xD382BF5, 0x80000000, instance_id.value
            print(new_tgi)
            footprint_areas = footprint_chunk.footprint_areas
            routing_areas = footprint_chunk.routing_areas
            footprint_name = ""
            for obj in valid_objs:
                print(obj, instance_id, hash_name_or_get_hash_64(obj.footprint_name))

                if hash_name_or_get_hash_64(obj.footprint_name).value == instance_id.value:
                    footprint_name = obj.footprint_name
                    print(obj.footprint_resource_variant, obj.footprint_resource_variant == "World Camera Bounds")
                    if obj.footprint_resource_variant == "World Camera Bounds" or obj.footprint_resource_variant == "World Allowed Routing":
                        # Footprint is WorldLandingStripResource
                        new_tgi.t = 0x4F726BBE
                    points = self.sort_vertices_clockwise(obj)
                    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

                    area = Area()
                    self.create_area(obj, area, points, context)

                    if area.bounding_box.max_y > max_height:
                        max_height = area.bounding_box.max_y
                    if area.bounding_box.min_y < min_height:
                        min_height = area.bounding_box.min_y

                    if obj.is_routing_footprint:
                        max_height = 0
                        min_height = 0
                        area.bounding_box.max_y = 0
                        area.bounding_box.min_y = 0
                        routing_areas.append(area)
                    else:
                        footprint_areas.append(area)
            footprint_chunk.minimum_height, footprint_chunk.maximum_height = min_height, max_height
            rcol.internal_tgis.append(new_tgi)

            rcol.update_chunk_position_size_automatically(0)

            all_data = io.BytesIO()
            default_export_path = os.path.join(os.environ["HOMEPATH"], "Desktop") + os.sep + "Animation Workspace"
            selected_export_path = context.scene.s4animtools_export_path
            if selected_export_path == "":
                selected_export_path = default_export_path

            if not os.path.exists(selected_export_path):
                os.mkdir(selected_export_path)
            try:
                s4animtools.serialization.recursive_write([*rcol.serialize()], all_data)
            except:
                print(traceback.format_exc())

            with open(os.path.join(selected_export_path,
                                   f"{hex(new_tgi.t).upper()[2:]}!80000000!{hex(new_tgi.i).upper()[2:]}.{footprint_name}.Footprint.binary"),
                      "wb") as file:
                file.write(all_data.getvalue())

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        return {"FINISHED"}

    def get_angle(self, vertex, center):
        return pi - math.atan2(vertex[1] - center[1], vertex[0] - center[0])

    def sort_vertices_clockwise(self, obj):
        points = []
        me = obj.data
        bm = bmesh.new()
        bm.from_mesh(me)
        verts = bm.verts[:]

        center_position_x = 0
        center_position_y = 0
        vert_count = len(verts)

        for vert in verts:
            center_position_x += vert.co.x
            center_position_y += vert.co.y

        center_position_x /= vert_count
        center_position_y /= vert_count

        verts.sort(key=lambda v: self.get_angle(v.co.xy, (center_position_x, center_position_y)))
        verts.insert(0, verts.pop())
        for i, v in enumerate(verts):
            v.index = i
            points.append((v.co[0], -v.co[1]))
        bm.verts.sort()
        bm.to_mesh(me)
        me.update()
        return points


class OT_S4ANIMTOOLS_VisualizeFootprint(bpy.types.Operator):
    bl_idname = "s4animtools.visualize_footprint"
    bl_label = "Visualize Footprint"
    bl_options = {"REGISTER", "UNDO"}

    command: bpy.props.StringProperty()

    def execute(self, context):
        if "Green_Visualization_Color" not in bpy.data.materials:
            green_material = bpy.data.materials.new("Green_Visualization_Color")
            green_material.use_nodes = True
            tree = green_material.node_tree
            nodes = tree.nodes
            bsdf = nodes["Principled BSDF"]
            bsdf.inputs["Base Color"].default_value = (0, 1, 0, 1)
            green_material.diffuse_color = (0, 1, 0, 1)
        if "Red_Visualization_Color" not in bpy.data.materials:
            green_material = bpy.data.materials.new("Red_Visualization_Color")
            green_material.use_nodes = True
            tree = green_material.node_tree
            nodes = tree.nodes
            bsdf = nodes["Principled BSDF"]
            bsdf.inputs["Base Color"].default_value = (1, 0, 0, 1)
            green_material.diffuse_color = (1, 0, 0, 1)

        red_material = bpy.data.materials["Red_Visualization_Color"]
        green_material = bpy.data.materials["Green_Visualization_Color"]
        for obj in bpy.data.objects:
            if obj.is_footprint:
                if self.command == "for_placement":
                    if obj.for_placement:
                        obj.active_material = green_material
                    else:
                        obj.active_material = red_material
                elif self.command == "for_pathing":
                    if obj.for_pathing:
                        obj.active_material = green_material
                    else:
                        obj.active_material = red_material
                elif self.command == "pool":
                    if obj.pool:
                        obj.active_material = green_material
                    else:
                        obj.active_material = red_material
                elif self.command == "terrain":
                    if obj.terrain:
                        obj.active_material = green_material
                    else:
                        obj.active_material = red_material
                elif self.command == "floor":
                    if obj.floor:
                        obj.active_material = green_material
                    else:
                        obj.active_material = red_material
        return {"FINISHED"}


if __name__ == "__main__":
    pass
