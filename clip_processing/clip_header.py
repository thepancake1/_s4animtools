import io
import os
import s4animtools.clip_processing
import s4animtools.serialization
from s4animtools import slot_assignments
from s4animtools.serialization.types.transforms import Quaternion, Vector3
from s4animtools.serialization.types.basic import u32, f32, String, Bytes
from s4animtools.clip_processing.clip_body import ClipBody, ClipBodyTS3
from s4animtools.serialization import get_binary_size, get_size, concatenate_bytes
from s4animtools.serialization.fnv import get_64bithash
from s4animtools.serialization.types.strings import IOString
from s4animtools.slot_assignments import SlotAssignment, SlotAssignmentListTS3
from s4animtools.stream import FileReader

FPS = 30

# TODO need to remove all other duplicated instances of this list

bone_to_slot_offset_idx = {"b__L_Hand__" : 0, "b__R_Hand__" : 1,
                           "b__L_Foot__" : 2, "b__R_Foot__" : 3,
                           "b__ROOT_bind__" : 4}


class ExplicitNamespace:
    def __init__(self, value):
        self.length = len(value)
        self.value = value

    def to_binary(self):
        return u32(self.length).to_binary() + self.value.encode("ascii")


class BaseClipResource:
    pass

class ClipResourceTS4(BaseClipResource):
    def __init__(self, clip_name, rig_name, slot_assignments:list[SlotAssignment], explicit_namespaces, reference_namespace_hash, initial_offset_q,
                 initial_offset_t, source_file_name, loco_animation,disable_rig_suffix, version=14,
                    surface_namespace_hash=2166136261, surface_joint_name_hash=2166136261, surface_child_namespace_hash=2166136261,
                 duration=0, flags=0):
        # If version number were to ever be updated to include later versions, make sure to remember that events and strings were updated.
        if version is None:
            self.version = 14

        else:
            self.version = version
        self.s3pe_naming = False
        self.flags = flags
        if loco_animation:
            self.flags |= 1
        self.duration = duration
        self.initial_offset_q = initial_offset_q
        self.initial_offset_t =  initial_offset_t
        self.reference_namespace_hash = reference_namespace_hash
        self.surface_namespace_hash = surface_namespace_hash
        self.surface_joint_name_hash = surface_joint_name_hash
        self.surface_child_namespace_hash = surface_child_namespace_hash
        if disable_rig_suffix:
            #TODO Hack to support sims 4 pose packs from s4s
            encoded_clipname = clip_name
            export_filename = clip_name.replace(":PosePack", "_PosePack")
        else:
            encoded_clipname = "{}_{}".format(clip_name, rig_name)
            export_filename = encoded_clipname

        self.clip_name = encoded_clipname
        self.file_name = export_filename
        self.rig_name = rig_name
        self.explicit_namespace_count = len(explicit_namespaces)
        self.explicit_namespaces = []
        for namespace in explicit_namespaces:
            if isinstance(namespace, ExplicitNamespace):
                self.explicit_namespaces.append(namespace)
            else:
                self.explicit_namespaces.append(ExplicitNamespace(namespace))
        self.slot_assignments = slot_assignments
        self.slot_assignment_count = len(slot_assignments)
        self.clip_event_list = []
        self.codec_data_length = 0
        self.clip_body = ClipBody(self.clip_name, source_file_name)

    @property
    def clip_name_length(self):
        return len(self.clip_name)

    @property
    def rig_name_length(self):
        return len(self.rig_name)

    @property
    def file_name_length(self):
        return len(self.file_name)

    @property
    def clip_event_count(self):
        return len(self.clip_event_list)

    def update_duration(self, ticks):
        # -1 tick for some reason.
        self.duration = ticks / FPS
        self.clip_body.set_clip_length(ticks)


    def add_event(self, event):
        self.clip_event_list.append(event)

    def get_clip_filename(self):
        if self.s3pe_naming:
            return "S4_6B20C4F3_00000000_{}_{}.Clip".format(get_64bithash(self.clip_name), self.file_name)
        return "6B20C4F3!00000000!{}.{}.Clip".format(get_64bithash(self.clip_name), self.file_name)

    def get_clip_header_filename(self):
        if self.s3pe_naming:
            return "S4_BC4A5044_00000000_{}_{}.ClipHeader".format(get_64bithash(self.clip_name), self.file_name)
        return "BC4A5044!00000000!{}.{}.ClipHeader".format(get_64bithash(self.clip_name), self.file_name)
    def get_loose_clip_naming(self):
        return "0x00000000!0x{}.6b20c4f3".format(get_64bithash(self.clip_name).lower())
    def get_loose_clip_header_naming(self):
        return "0x00000000!0x{}.bc4a5044".format(get_64bithash(self.clip_name).lower())

    def export(self, export_path, alternative_export_path, export_as_loose_filenames):
        import bpy
        export_bytes = self.to_binary()
        anim_path = os.path.abspath(export_path)

        if export_path.startswith(".\\"):
            filepath = bpy.data.filepath
            anim_path = os.path.join(os.path.dirname(os.path.dirname(filepath)), export_path[2:])

        if export_path == "":
            anim_path = os.path.join(os.path.expanduser("~/Desktop"), "Animation Workspace")
        if not os.path.exists(anim_path):
            os.mkdir(anim_path)
        clip_filename = ""
        clip_header_filename = ""
        if export_as_loose_filenames:
            clip_filename = self.get_loose_clip_naming()
            clip_header_filename = self.get_loose_clip_header_naming()
        else:
            clip_filename = self.get_clip_filename()
            clip_header_filename = self.get_clip_header_filename()


        try:
            with open(os.path.join(anim_path, clip_filename), "wb") as file:
                file.write(export_bytes)
                with open(os.path.join(anim_path, clip_header_filename), "wb") as clip_header_file:
                    clip_header_file.write(export_bytes)

            if alternative_export_path != "":
                with open(os.path.join(alternative_export_path, self.get_clip_filename()), "wb") as clip_file:
                    clip_file.write(export_bytes)
                with open(os.path.join(alternative_export_path, self.get_clip_header_filename()), "wb") as clip_header_file:
                    clip_header_file.write(export_bytes)
        except Exception as e:
            print(e)

    @staticmethod
    def from_binary(reader):
        version = reader.u32()
        if version > 18:
            raise ValueError("TS4 Clip version {} is not supported.".format(version))
        flags = reader.u32()
        duration = reader.f32()
        initial_offset_q = Quaternion.from_binary(reader)
        initial_offset_t = Vector3.from_binary(reader)
        reference_namespace_hash = 0
        if version >= 5:
            reference_namespace_hash = reader.u32()
        surface_namespace_hash = 2166136261
        surface_joint_name_hash = 2166136261
        surface_child_namespace_hash = 2166136261
        if version >= 10:
            surface_namespace_hash = reader.u32()
            surface_joint_name_hash = reader.u32()

        if version >= 11:
            surface_child_namespace_hash = reader.u32()
        clip_name = ""
        if version >= 7:
            clip_name = IOString.from_binary(reader).string


        rig_namespace = IOString.from_binary(reader).string
        explicit_namespaces = []
        if version >= 4:
            explicit_namespace_count = reader.u32()
            for _ in range(explicit_namespace_count):
                explicit_namespaces.append(String(IOString.from_binary(reader).string))

        slot_assignment_count = reader.u32()
        slot_assignments = []
        for _ in range(slot_assignment_count):
            slot_assignments.append(SlotAssignment.from_binary(reader))


        clip = ClipResourceTS4(clip_name, rig_namespace, slot_assignments, explicit_namespaces, reference_namespace_hash, initial_offset_q,
                               initial_offset_t,"", False, disable_rig_suffix=True,
                               version=version, surface_namespace_hash=surface_namespace_hash,
                               surface_joint_name_hash=surface_joint_name_hash,
                               surface_child_namespace_hash=surface_child_namespace_hash, duration=duration, flags=flags)


    def to_binary(self):
        serialized = [u32(self.version), u32(self.flags), f32(self.duration),
                      *self.initial_offset_q.to_binary(), *self.initial_offset_t.to_binary(),
                      u32(self.reference_namespace_hash), u32(self.surface_namespace_hash),
                      u32(self.surface_joint_name_hash), u32(self.surface_child_namespace_hash),
                      u32(self.clip_name_length), String(self.clip_name),
                      u32(self.rig_name_length), String(self.rig_name), u32(self.explicit_namespace_count),
                      *self.explicit_namespaces,
                      u32(self.slot_assignment_count), *self.slot_assignments, u32(self.clip_event_count),
                      *self.clip_event_list, u32(self.codec_data_length)]
        header_data = []

        header_length = 0
        for item in serialized:
            serialized_data = item.to_binary()
            header_data.append(serialized_data)
        header_length += get_size(header_data)
        print(self.clip_body)
        clip_body = self.clip_body.to_binary()

        actual_codec_data_length = len(clip_body)
        # Replace codec data length with actual one
        print(header_data)
        header_data[-1] = u32(actual_codec_data_length).to_binary()
        return concatenate_bytes([header_data, clip_body])

# Todo should probably find a better spot for this
class ClipEventsTS3:
    def __init__(self, events):
        self.version = 0x103
        self.size = 0
        # =CE=
        self.magic = 0x3D45433D
        self.events = events

    @property
    def event_count(self):
        return len(self.events)


    def from_binary(self, reader):
        self.magic = reader.u32()
        count = reader.u32()
        size  = reader.u32()
        self.size = size
        start_offset = reader.u32()

    def to_binary(self):
        b = bytearray()
        b.extend(u32(self.magic).to_binary())
        b.extend(u32(self.event_count).to_binary())
        b.extend(u32(self.size).to_binary())
        b.extend(u32(0).to_binary())
        return b


class ClipResourceTS3(BaseClipResource):
    def __init__(self, clip_name, rig_name, source_file_name, loco_animation,disable_rig_suffix, version=2,
                 duration=0, flags=0, group_id=0):
        # If version number were to ever be updated to include later versions, make sure to remember that events and strings were updated.
        self.end_offset = 0
        self.clip_offset = 44
        self.slot_offset = 0
        self.actor_offset = 0
        self.event_offset = 0
        self.unknown_offset = 0

        self.unknown_value = 0
        self.unknown_value2 = 1
        if version is None:
            self.version = 2

        else:
            self.version = version
        self.s3pe_naming = True
        self.flags = flags
        self.resource_type = 0x6B20C4F3
       # if loco_animation:
       #     self.flags |= 1
        self.duration = duration
        if disable_rig_suffix:
            #TODO Hack to support sims 4 pose packs from s4s
            encoded_clipname = clip_name
            export_filename = clip_name.replace(":PosePack", "_PosePack")
        else:
            encoded_clipname = "{}_{}".format(clip_name, rig_name)
            export_filename = encoded_clipname

        self.clip_name = export_filename
        self.rig_name = rig_name
        self.codec_data_length = 0
        self.clip_body = ClipBodyTS3(self.clip_name, source_file_name)
        self.clip_events = ClipEventsTS3([])
        self.slot_assignment_list = SlotAssignmentListTS3([])
        self.file_name = export_filename
        self.group_id = group_id
    @property
    def clip_name_length(self):
        return len(self.clip_name)

    @property
    def rig_name_length(self):
        return len(self.rig_name)

    @property
    def file_name_length(self):
        return len(self.file_name)

    @property
    def clip_event_count(self):
        return len(self.clip_event_list)

    def update_duration(self, ticks):
        # -1 tick for some reason.
        self.duration = ticks / FPS
        self.clip_body.set_clip_length(ticks)


    def add_event(self, event):
        # TODO Update this for ts3
        self.clip_event_list.append(event)

    def get_clip_filename(self):
        group_id_string = "0x{:08x}".format(self.group_id)

        if self.s3pe_naming:
            return "S3_{}_00000000_{}_{}.animation".format(group_id_string, get_64bithash(self.clip_name), self.file_name)
        # I should probably remove this, since everybody is probably using s3pe for sims 3
        return "6B20C4F3!{}!{}.{}.Clip".format(group_id_string, get_64bithash(self.clip_name), self.file_name)

    def get_loose_clip_naming(self):
        group_id_string = "0x{:08x}".format(self.group_id)
        return "{}!0x{}.6b20c4f3".format(group_id_string, get_64bithash(self.clip_name).lower())

    def export(self, export_path, alternative_export_path, export_as_loose_filenames):
        import bpy
        export_bytes = self.to_binary()
        anim_path = os.path.abspath(export_path)

        if export_path.startswith(".\\"):
            filepath = bpy.data.filepath
            anim_path = os.path.join(os.path.dirname(os.path.dirname(filepath)), export_path[2:])

        if export_path == "":
            anim_path = os.path.join(os.path.expanduser("~/Desktop"), "Animation Workspace")
        if not os.path.exists(anim_path):
            os.mkdir(anim_path)
        clip_filename = ""
        if export_as_loose_filenames:
            clip_filename = self.get_loose_clip_naming()
        else:
            clip_filename = self.get_clip_filename()


        try:
            with open(os.path.join(anim_path, clip_filename), "wb") as file:
                file.write(export_bytes)

            if alternative_export_path != "":
                with open(os.path.join(alternative_export_path, self.get_clip_filename()), "wb") as clip_file:
                    clip_file.write(export_bytes)

        except Exception as e:
            print(e)

    @staticmethod
    def from_binary(reader):
        version = reader.u32()
        if version > 2:
            raise ValueError("TS3 Clip version {} is not supported.".format(version))
        flags = reader.u32()
        duration = reader.f32()

        rig_namespace = IOString.from_binary(reader).string
        explicit_namespaces = []
        if version >= 4:
            explicit_namespace_count = reader.u32()
            for _ in range(explicit_namespace_count):
                explicit_namespaces.append(String(IOString.from_binary(reader).string))

        slot_assignment_count = reader.u32()
        slot_assignments = []
        for _ in range(slot_assignment_count):
            slot_assignments.append(SlotAssignment.from_binary(reader))


    def to_binary(self):
        serialized = [u32(self.resource_type), u32(self.unknown_offset),
                      u32(self.codec_data_length),
                      u32(self.clip_offset), u32(self.slot_offset), u32(self.actor_offset), u32(self.event_offset),
                      u32(self.unknown_value), u32(self.unknown_value2), u32(self.end_offset), Bytes(bytes([0]* 16))]
        header_data = []

        header_length = 0
        for item in serialized:
            serialized_data = item.to_binary()
            header_data.append(serialized_data)
        header_length += get_size(header_data)
        print(self.clip_body)
        clip_body = self.clip_body.to_binary()

        actual_codec_data_length = len(clip_body)
        # Replace codec data length with actual one
        print(header_data)
        header_data[2] = u32(actual_codec_data_length).to_binary()
        slot_assignments_offset = len(concatenate_bytes([header_data, clip_body]))
        header_data[4] = u32(slot_assignments_offset-16).to_binary()

        before_rig_name_padding = slot_assignments_offset % 4
        before_rig_name_padding_bytes = bytearray([0x7e] * before_rig_name_padding)
        clip_name_offset = len(concatenate_bytes([header_data, clip_body, self.slot_assignment_list.to_binary(), before_rig_name_padding_bytes]))
        header_data[5] = u32(clip_name_offset- 20).to_binary()
        before_event_offset_padding = clip_name_offset % 4
        event_padding = bytearray([0x7e] * before_event_offset_padding)
        header_data[6] = u32(clip_name_offset - 24 + before_event_offset_padding).to_binary()

        header_data[9] = u32(len(concatenate_bytes([header_data, clip_body, self.slot_assignment_list.to_binary(), before_rig_name_padding_bytes,  self.rig_name.encode("ascii"), bytearray([0x00]), event_padding, self.clip_events.to_binary()])) - 36).to_binary()


        return concatenate_bytes([header_data, clip_body, self.slot_assignment_list.to_binary(), before_rig_name_padding_bytes,  self.rig_name.encode("ascii"), bytearray([0x00]), event_padding, self.clip_events.to_binary(), f32(0).to_binary(), f32(0).to_binary(), f32(0).to_binary(), f32(1).to_binary()])

    def add_slot_assignment(self, ik_chain_bone, target_actor_name, target_bone_name):
        self.slot_assignment_list.add_slot_assignment(bone_to_slot_offset_idx[ik_chain_bone], target_actor_name, target_bone_name)



if __name__ == "__main__":
    #clip = ClipResourceTS4.from_binary(reader=FileReader(r"D:\Assets\Resources\1.114 Clips Hold 2\6B20C4F3!00000000!1DEC500053B15F0B.a_loco_run_turnAndStop_0_x.Clip"))
    clip = ClipResourceTS3("a2o_dance", "x", "a2o_dance_x.blend", False, False)
    clip.add_slot_assignment( "b__L_Hand__", "x", "b__L_ThighTarget_slot")
    clip.add_slot_assignment( "b__L_Hand__", "x", "b__L_ThighFrontTarget_slot")
    clip.add_slot_assignment( "b__R_Hand__", "x", "b__R_ThighTarget_slot")
    clip.add_slot_assignment( "b__R_Hand__", "x", "b__R_ThighFrontTarget_slot")
    clip.add_slot_assignment( "b__L_Foot__", "x", "L_footWorld")
    clip.add_slot_assignment( "b__R_Foot__", "x", "R_footWorld")
    clip.add_slot_assignment( "b__ROOT_bind__", "x", "rootWorld")

    clip_bytes = clip.to_binary()
    with open(r"D:\testing\test ts3 clip.clip", "wb") as file:
        file.write(clip_bytes)