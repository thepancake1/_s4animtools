import io

from _s4animtools.clip_processing.value_types import uint32, float32, serializable_string
import os
import _s4animtools.clip_processing
from _s4animtools.clip_processing.clip_body import ClipBody
import importlib
from _s4animtools.clip_processing.test_tool import get_size, get_hash_from_bone_name, get_64bithash
from _s4animtools.rig_namepsaces import SlotAssignment
importlib.reload(_s4animtools.clip_processing.clip_body)

bone_to_slot_offset_idx = {"b__L_Hand__" : 0, "b__R_Hand__" : 1,
                           "b__L_Foot__" : 2, "b__R_Foot__" : 3,
                           "b__ROOT_bind__" : 4}


class ExplicitNamespace:
    def __init__(self, value):
        self.length = len(value)
        self.value = value

    def serialize(self):
        return uint32(self.length).serialize() + self.value.encode("ascii")
class ClipResource:
    def __init__(self, clip_name, rig_name, slot_assignments, explicit_namespaces, reference_namespace_hash, initial_offset_q,
                 initial_offset_t, source_file_name, loco_animation,disable_rig_suffix):
        # Current version number
        self._version = 14
        self.s3peNaming = False
        self._flags = 0
        if loco_animation:
            self._flags = 1
        self._duration = 0
        self._initialOffsetQ = list(map(float, initial_offset_q.split(",")))
        self._initialOffsetT = list(map(float, initial_offset_t.split(",")))
        if len(self._initialOffsetT) != 3:
            raise Exception(f"invalid initial offset T, expected 3 values. Got {len(self._initialOffsetT)}")

        if len(self._initialOffsetQ) != 4:
            raise Exception(f"invalid initial offset Q, expected 4 values. Got {len(self._initialOffsetQ)}")
        self.referenceNamespaceHash = int(reference_namespace_hash, 16)
        #TODO Add support for user-specified namespace hashes
        self.surfaceNamespaceHash = 2166136261
        self.surfaceJointNameHash = 2166136261
        self.surfaceChildNamespaceHash = 2166136261
        if disable_rig_suffix:
            #TODO Hack to support sims 4 pose packs from s4s
            encoded_clipname = clip_name
            export_filename = clip_name.replace(":PosePack", "_PosePack")
        else:
            encoded_clipname = "{}_{}".format(clip_name, rig_name)
            export_filename = encoded_clipname

        self.clipNameLength, self.clipName = len(encoded_clipname), encoded_clipname
        self.fileNameLength, self.fileName = len(export_filename), export_filename
        self.rigNameLength, self.rigName = len(rig_name), rig_name
        self.explicitNamespaceCount = 0
        self.explicitNamespaces = []
        self.slotAssignmentCount = 5
        self.slotAssignments = []
        slot_idx = 0
        # TODO Huh??? What does this do??
        for i in range(5):
            sA = SlotAssignment(i, 0, rig_name.encode("ascii"), b"b__ROOT__")
            self.slotAssignments.append(sA)

        for chain_bone in slot_assignments:
            for idx, slot_assignment in enumerate(slot_assignments[chain_bone]):
            # TODO Jesus christ, replace this with a class
                target_rig = slot_assignment[1]
                target_bone = slot_assignment[2]
                chain_idx = slot_assignment[4]
                if "subroot" in target_bone:
                    target_bone = "b__ROOT__"
                if target_bone.endswith("Adjust"):
                    target_bone = target_bone.replace("Adjust", "")
                # + 2 offset for consistency
                if chain_idx == -1:
                    chain_idx = bone_to_slot_offset_idx[slot_assignment[0]]
                sA = SlotAssignment(chain_idx, idx+1, target_rig.name.encode('ascii'), target_bone.encode('ascii'))
                self.slotAssignments.append(sA)
                # TODO Have more than one slot assignment per ik slot idx. Right now, one slot idx equals one target idx.
                slot_idx += 1

        self.slotAssignmentCount += slot_idx
        self.clipEventCount = 0
        self.clipEventList = []
        self.codecDataLength = 1 #Offset to end file I think. Remember to actually set this
        self.clip_body = ClipBody(self.clipName, source_file_name)
        # TODO WHAT IS GOING ON???
        if len(explicit_namespaces) >= 2:
            for namespace in explicit_namespaces.split(","):
                self.add_explicit_namespace(namespace.lstrip())

    def update_duration(self, ticks):
        # -1 tick for some reason.
        self._duration = (ticks) / 30 - (1/30)

    def add_explicit_namespace(self, name):
        self.explicitNamespaceCount += 1
        self.explicitNamespaces.append(ExplicitNamespace(name))

    def add_event(self, event):
        self.clipEventList.append(event)
        self.clipEventCount += 1

    def get_filename(self):
        if self.s3peNaming:
            return "S4_6B20C4F3_00000000_{}_{}.Clip".format(get_64bithash(self.clipName), self.fileName)
        return "6B20C4F3!00000000!{}.{}.Clip".format(get_64bithash(self.clipName), self.fileName)

    def get_header_name(self):
        if self.s3peNaming:
            return "S4_BC4A5044_00000000_{}_{}.ClipHeader".format(get_64bithash(self.clipName), self.fileName)

        return "BC4A5044!00000000!{}.{}.ClipHeader".format(get_64bithash(self.clipName), self.fileName)

    def serialize(self):

        anim_path = os.path.expanduser("~/Desktop") + os.sep + "Animation Workspace"
        if not os.path.exists(anim_path):
            os.mkdir(anim_path)

        with open(anim_path + os.sep +  self.get_filename(), "wb") as file:
            serialized = [uint32(self._version), uint32(self._flags), float32(self._duration),
                          *map(float32, self._initialOffsetQ), *map(float32, self._initialOffsetT),
                          uint32(self.referenceNamespaceHash), uint32(self.surfaceNamespaceHash),
                          uint32(self.surfaceJointNameHash), uint32(self.surfaceChildNamespaceHash),
                          uint32(self.clipNameLength), serializable_string(self.clipName),
                          uint32(self.rigNameLength), serializable_string(self.rigName), uint32(self.explicitNamespaceCount), *self.explicitNamespaces,
                          uint32(self.slotAssignmentCount), *self.slotAssignments, uint32(self.clipEventCount), *self.clipEventList, uint32(self.codecDataLength)]
            header_data = []

            header_length = 0
            for item in serialized:
                serialized_data = item.serialize()
                header_data.append(serialized_data)
                header_length += get_size(serialized_data)

            clip_body, frame_data = self.clip_body.serialize()

            actualCodecDataLength = get_size(clip_body) + get_size(frame_data)
            # Replace codec data length with actual one
            header_data[-1] = uint32(actualCodecDataLength).serialize()
            all_data = io.BytesIO()
            # offsets

            _s4animtools.clip_processing.test_tool.recursive_write([*header_data, clip_body, frame_data], all_data)
            write_data = all_data.getvalue()

            file.write(write_data)
            with open(anim_path + os.sep + self.get_header_name(), "wb") as clip_header_file:
                clip_header_file.write(write_data)
if __name__ == "__main__":
    ClipResource().serialize()