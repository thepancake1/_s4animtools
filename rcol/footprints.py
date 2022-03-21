from _s4animtools.serialization.types.basic import UInt32, Float32
from _s4animtools.serialization.types.basic import Byte, Bytes
from _s4animtools.serialization.types.tgi import TGI
from _s4animtools.stream import StreamReader
def get_combined_len(value):
    size = 0
    if isinstance(value, list):
        for item in value:
            size += len(item)
    else:
        return len(value)
    return size

class PolygonHeightOverride:
    def __init__(self):
        self.name_hash = 0
        self.height = 0

    def read(self, reader:StreamReader):
        self.name_hash = reader.u32()
        self.height = reader.float32()
        return self

    def serialize(self):
        data = [UInt32(self.name_hash), UInt32(self.height)]

        serialized_stuff = []
        total_len = 0
        for value in data:
            serialied = value.serialize()
            serialized_stuff.append(serialied)
        return serialized_stuff

class FootprintPolyFlags:
    def __init__(self):
        self.for_placement = False
        self.for_pathing = False
        self.is_enabled = False
        self.discouraged = False
        self.landing_strip = False
        self.no_raycast= False
        self.placement_slotted = False
        self.encouraged = False
        self.terrain_cutout = False

    @property
    def bitfield(self):
        return  (int(self.terrain_cutout) >> 8) + (int(self.encouraged) >> 7) + (int(self.placement_slotted) >> 6) + \
                (int(self.no_raycast) >> 5) + (int(self.landing_strip) >> 4) + (int(self.discouraged) >> 3) + \
                (int(self.is_enabled) >> 2) + (int(self.for_pathing) >> 1) + int(self.for_placement)

    @bitfield.setter
    def bitfield(self, value):
        bitstring = "{:08b}".format(value)
        print(bitstring)
        self.terrain_cutout = bitstring[-9]
        self.encouraged = bitstring[-8]
        self.placement_slotted = bitstring[-7]
        self.no_raycast = bitstring[-6]
        self.landing_strip = bitstring[-5]
        self.discouraged = bitstring[-4]
        self.is_enabled = bitstring[-3]
        self.for_pathing = bitstring[-2]
        self.for_placement = bitstring[-1]
        print(str(self))
    def __str__(self):
        return "Terrain Cutout: {}\n" \
               "Encouraged: {}\n" \
               "Placement Slotted: {}\n" \
               "No Raycast: {}\n" \
               "Landing Strip: {}\n" \
               "Discouraged: {}\n" \
               "Is Enabled: {}\n" \
               "For Pathing: {}\n" \
               "For Placement: {}\n".format(self.terrain_cutout, self.encouraged, self.placement_slotted, self.no_raycast, self.landing_strip,
                                            self.discouraged, self.is_enabled, self.for_pathing, self.for_placement)
    def read(self, reader:StreamReader):
        self.bitfield = reader.u32()

    def serialize(self):
        data = [UInt32(self.bitfield)]

        serialized_stuff = []
        for value in data:
            serialied = value.serialize()
            serialized_stuff.append(serialied)
        return serialized_stuff

class BoundingBox:
    def __init__(self):
        self.min_x = 0
        self.max_x = 0
        self.min_y = 0
        self.max_y = 0
        self.min_z = 0
        self.max_z = 0

    def read(self, reader:StreamReader):
        self.min_x = reader.float32()
        self.min_z = reader.float32()
        self.max_x = reader.float32()
        self.max_z = reader.float32()
        self.min_y = reader.float32()
        self.max_y = reader.float32()
        return self
    def serialize(self):
        data = [Float32(self.min_x), Float32(self.max_x), Float32(self.min_y), Float32(self.max_y),
                Float32(self.max_z), Float32(self.max_z)]

        serialized_stuff = []
        total_len = 0
        for value in data:
            serialied = value.serialize()
            serialized_stuff.append(serialied)
        return serialized_stuff


class Point:
    def __init__(self):
        self.x = 0
        self.z = 0

    def read(self, reader:StreamReader):
        self.x = reader.float32()
        self.z = reader.float32()
        return self


    def serialize(self):
        data = [Float32(self.x), Float32(self.z)]

        serialized_stuff = []
        total_len = 0
        for value in data:
            serialied = value.serialize()
            serialized_stuff.append(serialied)
        return serialized_stuff

class Area:
    def __init__(self):
        self.name_hash = 0
        self.priority = 0
        self.area_type_flags = 0
        self.points = []
        self.intersection_object_type = 0
        self.allow_intersection_types = 0
        self.surface_type_flags = 0
        self.surface_attribute_flags = 0
        self.deprected_level_offset = 0
        self.bounding_box = BoundingBox()

    @property
    def point_count(self):
        return len(self.points)

    def read(self, reader:StreamReader):
        self.name_hash = reader.u32()
        self.priority =  reader.u8()
        self.area_type_flags = reader.u32()
        point_count = reader.u8()
        for i in range(point_count):
            self.points.append(Point().read(reader))
        self.intersection_object_type =  reader.u32()
        self.allow_intersection_types =  reader.u32()
        self.surface_type_flags =  reader.u32()
        self.surface_attribute_flags =  reader.u32()
        self.deprected_level_offset =  reader.u8()
        self.bounding_box = BoundingBox().read(reader)
        return self

    def serialize(self):
        data = [UInt32(self.name_hash), Byte(self.priority), UInt32(self.area_type_flags),
                Byte(self.point_count), *self.points,
                UInt32(self.intersection_object_type), UInt32(self.allow_intersection_types),
                UInt32(self.surface_type_flags), UInt32(self.surface_attribute_flags),
                Byte(self.deprected_level_offset), self.bounding_box]

        serialized_stuff = []
        total_len = 0
        for value in data:
            serialied = value.serialize()
            serialized_stuff.append(serialied)
            total_len += get_combined_len(serialied)
        return serialized_stuff


class Footprint:
    def __init__(self, identifier=0):
        self.identifier = identifier
        self.version = 0
        self.template_key = TGI()
        self.min_height_overrides = []
        self.max_height_overrides = []

        self.footprint_areas = []
        self.slot_areas = []
        self.maximum_height = 0
        self.minimum_height = 0

    @property
    def min_height_override_count(self):
        return len(self.min_height_overrides)
    @property
    def max_height_override_count(self):
        return len(self.max_height_overrides)
    @property
    def footprint_areas_count(self):
        return len(self.footprint_areas)
    @property
    def slot_areas_count(self):
        return len(self.slot_areas)

    def read(self, reader:StreamReader):
        self.identifier = reader.u32()
        self.version = reader.u32()
        self.template_key = TGI().read(reader)
        if self.template_key.t != 0:
            minimum_height_override_count = reader.u8()
            for i in range(minimum_height_override_count):
                self.min_height_overrides.append(PolygonHeightOverride().read(reader))

            maximum_height_override_count = reader.u8()
            for i in range(maximum_height_override_count):
                self.max_height_overrides.append(PolygonHeightOverride().read(reader))

        else:
            footprint_area_count = reader.u8()
            for i in range(footprint_area_count):
                self.footprint_areas.append(Area().read(reader))

            slot_area_count = reader.u8()
            for i in range(slot_area_count):
                self.slot_areas.append(Area().read(reader))
            self.minimum_height = reader.float32()
            self.maximum_height = reader.float32()
        return self
    def serialize(self):
        serialized_stuff = []
        if self.template_key.t != 0:
            subdata = [Byte(self.min_height_override_count), *self.min_height_overrides,
                           Byte(self.max_height_override_count),
                           *self.max_height_overrides]

        else:
            subdata = [Byte(self.footprint_areas_count), *self.footprint_areas,
                           Byte(self.slot_areas_count),
                           *self.slot_areas, Float32(self.maximum_height), Float32(self.minimum_height)]
        data = [Bytes(self.identifier), UInt32(self.version), self.template_key, *subdata]

        for value in data:
            serialized_stuff.append(value.serialize())

        return serialized_stuff

