import io
import os
import importlib
import _s4animtools.clip_processing
import _s4animtools.serialization
from _s4animtools.serialization.types.basic import UInt32, Float32, String
from _s4animtools.clip_processing.clip_body import ClipBody
from _s4animtools.serialization import get_size
from _s4animtools.serialization.fnv import get_64bithash
from _s4animtools.slot_assignments import SlotAssignment
importlib.reload(_s4animtools.clip_processing.clip_body)

bone_to_slot_offset_idx = {"b__L_Hand__" : 0, "b__R_Hand__" : 1,
                           "b__L_Foot__" : 2, "b__R_Foot__" : 3,
                           "b__ROOT_bind__" : 4}


class ExplicitNamespace:
    def __init__(self, value):
        self.length = len(value)
        self.value = value

    def serialize(self):
        return UInt32(self.length).serialize() + self.value.encode("ascii")
class ClipResource:
    def __init__(self, clip_name, rig_name, slot_assignments, explicit_namespaces, reference_namespace_hash, initial_offset_q,
                 initial_offset_t, source_file_name, loco_animation,disable_rig_suffix):
        # If version number were to ever be updated to include later versions, make sure to remember that events and strings were updated.
        self.version = 14
        self.s3pe_naming = False
        self.flags = 0
        if loco_animation:
            self.flags = 1
        self.duration = 0
        self.initial_offset_q = initial_offset_q
        self.initial_offset_t =  initial_offset_t
        #TODO Add support for user-specified namespace hashes
        self.reference_namespace_hash = reference_namespace_hash
        self.surface_namespace_hash = 2166136261
        self.surface_joint_name_hash = 2166136261
        self.surface_child_namespace_hash = 2166136261
        if disable_rig_suffix:
            #TODO Hack to support sims 4 pose packs from s4s
            encoded_clipname = clip_name
            export_filename = clip_name.replace(":PosePack", "_PosePack")
        else:
            encoded_clipname = "{}_{}".format(clip_name, rig_name)
            export_filename = encoded_clipname

        self.clip_name_length, self.clip_name = len(encoded_clipname), encoded_clipname
        self.file_name_length, self.file_name = len(export_filename), export_filename
        self.rig_name_length, self.rig_name = len(rig_name), rig_name
        self.explicit_namespace_count = 0
        self.explicit_namespaces = []
        self.slot_assignment_count = 0
        self.slot_assignments = []
        slot_idx = 0
        for chain_bone in slot_assignments:
            for idx, slot_assignment in enumerate(slot_assignments[chain_bone]):
                target_rig = slot_assignment.target_rig
                print("target rig is {}".format(target_rig))
                target_bone = slot_assignment.target_bone
                chain_idx = slot_assignment.chain_idx
                if "subroot" in target_bone:
                    target_bone = "b__ROOT__"
                if "loco" in target_bone:
                    target_bone = "b__ROOT__"
                if target_bone.endswith("Adjust"):
                    target_bone = target_bone.replace("Adjust", "")
                if chain_idx == -1:
                    chain_idx = bone_to_slot_offset_idx[slot_assignment.source_bone]
                sA = SlotAssignment(chain_idx, idx, target_rig.rig_name.encode('ascii'), target_bone.encode('ascii'))
                self.slot_assignments.append(sA)
                slot_idx += 1

        self.slot_assignment_count += slot_idx
        self.clipEventCount = 0
        self.clipEventList = []
        self.codecDataLength = 0
        self.clip_body = ClipBody(self.clip_name, source_file_name)
        if len(explicit_namespaces) >= 2:
            for namespace in explicit_namespaces.split(","):
                self.add_explicit_namespace(namespace.lstrip())

    def update_duration(self, ticks):
        # -1 tick for some reason.
        self.duration = ticks / 30 - (1 / 30)
        self.clip_body.set_clip_length(ticks)

    def add_explicit_namespace(self, name):
        self.explicit_namespace_count += 1
        self.explicit_namespaces.append(ExplicitNamespace(name))

    def add_event(self, event):
        self.clipEventList.append(event)
        self.clipEventCount += 1

    def get_clip_filename(self):
        if self.s3pe_naming:
            return "S4_6B20C4F3_00000000_{}_{}.Clip".format(get_64bithash(self.clip_name), self.file_name)
        return "6B20C4F3!00000000!{}.{}.Clip".format(get_64bithash(self.clip_name), self.file_name)

    def get_clip_header_filename(self):
        if self.s3pe_naming:
            return "S4_BC4A5044_00000000_{}_{}.ClipHeader".format(get_64bithash(self.clip_name), self.file_name)

        return "BC4A5044!00000000!{}.{}.ClipHeader".format(get_64bithash(self.clip_name), self.file_name)

    def export(self, export_path):
        import bpy
        anim_path = os.path.abspath(export_path)

        if export_path.startswith(".\\"):
            filepath = bpy.data.filepath
            anim_path = os.path.join(os.path.dirname(os.path.dirname(filepath)), export_path[2:])

        if export_path == "":
            anim_path = os.path.join(os.path.expanduser("~/Desktop"), "Animation Workspace")
        if not os.path.exists(anim_path):
            os.mkdir(anim_path)

        with open(os.path.join(anim_path, self.get_clip_filename()), "wb") as file:
            serialized = [UInt32(self.version), UInt32(self.flags), Float32(self.duration),
                          *self.initial_offset_q.to_binary(), *self.initial_offset_t.to_binary(),
                          UInt32(self.reference_namespace_hash), UInt32(self.surface_namespace_hash),
                          UInt32(self.surface_joint_name_hash), UInt32(self.surface_child_namespace_hash),
                          UInt32(self.clip_name_length), String(self.clip_name),
                          UInt32(self.rig_name_length), String(self.rig_name), UInt32(self.explicit_namespace_count), *self.explicit_namespaces,
                          UInt32(self.slot_assignment_count), *self.slot_assignments, UInt32(self.clipEventCount), *self.clipEventList, UInt32(self.codecDataLength)]
            header_data = []

            header_length = 0
            for item in serialized:
                serialized_data = item.serialize()
                header_data.append(serialized_data)
                header_length += get_size(serialized_data)

            clip_body, frame_data = self.clip_body.serialize()

            actual_codec_data_length = get_size(clip_body) + get_size(frame_data)
            # Replace codec data length with actual one
            header_data[-1] = UInt32(actual_codec_data_length).serialize()
            all_data = io.BytesIO()
            # offsets

            _s4animtools.serialization.recursive_write([*header_data, clip_body, frame_data], all_data)
            write_data = all_data.getvalue()

            file.write(write_data)
            with open(os.path.join(anim_path, self.get_clip_header_filename()), "wb") as clip_header_file:
                clip_header_file.write(write_data)
if __name__ == "__main__":
    ClipResource().serialize()