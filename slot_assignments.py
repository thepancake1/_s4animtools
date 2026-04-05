from typing import List

from s4animtools.serialization.types.basic import u32, u16
from s4animtools.serialization.types.strings import IOString, Byte512String


class SlotAssignment:
    def __init__(self, chain_idx, slot_idx, target_object_namespace, target_joint_name):
        self._chain_idx = chain_idx
        self._slot_idx = slot_idx
        self._actor = target_object_namespace
        self._target = target_joint_name

    @staticmethod
    def from_binary(reader):
        chain_idx = reader.u16()
        slot_idx = reader.u16()
        target_object_namespace = IOString.from_binary(reader).string
        target_joint_name = IOString.from_binary(reader).string
        return SlotAssignment(chain_idx, slot_idx, target_object_namespace, target_joint_name)

    def to_binary(self):
        return [u16(self._chain_idx).to_binary(),
                u16(self._slot_idx).to_binary(),
                IOString(self._actor).to_binary(),
                IOString(self._target).to_binary()]


class SlotAssignmentTS3:
    def __init__(self, slot_idx, target_object_namespace, target_joint_name):
        self._slot_idx = slot_idx
        self._actor = target_object_namespace
        self._target = target_joint_name

    @staticmethod
    def from_binary(reader):
        slot_idx = reader.u32()
        target_object_namespace = Byte512String.from_binary(reader).string
        target_joint_name = Byte512String.from_binary(reader).string
        return SlotAssignmentTS3(slot_idx, target_object_namespace, target_joint_name)

    def to_binary(self):
        to_bytes = [u32(self._slot_idx).to_binary(),
                Byte512String(self._actor).to_binary(),
                Byte512String(self._target).to_binary()]
        b = bytearray()
        for item in to_bytes:
            b.extend(item)
        return b

class SlotAssignmentIKChainTS3:
    def __init__(self, slot_assignments:List[SlotAssignmentTS3]):
        self.slot_assignments = slot_assignments

    @staticmethod
    def from_binary(reader):
        padding = reader.u32()
        slot_assignment_count = reader.u32()
        offsets = [reader.u32() for slot_assignment_idx in range(slot_assignment_count)]
        slot_assignments = [SlotAssignmentTS3.from_binary(reader) for slot_assignment_idx in range(slot_assignment_count)]
        return SlotAssignmentIKChainTS3(slot_assignments)
    def to_binary(self):
        padding = u32(2122219134).to_binary()
        # Like in SlotAssignmentListTS3
        # Offsets are the length of the table
        # plus the length of each slot_assignment in binary
        # each offset is 4 bytes, so 2 slot_assignments
        # equals 8 bytes for the table
        offsets = [0] * len(self.slot_assignments)
        slot_assignment_bytes = bytearray()
        for slot_assignment_idx in range(len(self.slot_assignments)):
            offsets[slot_assignment_idx] = len(slot_assignment_bytes) + (len(offsets) * 4)

            slot_assignment = self.slot_assignments[slot_assignment_idx]
            slot_assignment_bytes.extend(slot_assignment.to_binary())
        header_byte_array = bytearray()
        for offset in offsets:
            header_byte_array.extend(u32(offset).to_binary())
        return padding + u32(len(self.slot_assignments)).to_binary() + header_byte_array + slot_assignment_bytes



class SlotAssignmentListTS3:
    def __init__(self, ik_chains):
        self.ik_chains = ik_chains

    @staticmethod
    def from_binary(reader):
        count = reader.u32()
        for ik_chain_idx in range(count):
            offset = reader.u32()
        _ik_chains = []
        for ik_chain_idx in range(count):
            ik_chain = SlotAssignmentIKChainTS3.from_binary(reader)
            _ik_chains.append(ik_chain)
        return SlotAssignmentListTS3(_ik_chains)


    def to_binary(self):
        byte_array = bytearray()
        # Exporting offserts
        # Offsets are the length of the table
        # plus the length of each ik_chain in binary
        # each offset is 4 bytes, so 5 ik chains
        # equals 20 bytes for the table
        header_byte_array = bytearray()

        header_byte_array.extend(u32(len(self.ik_chains)).to_binary())
        print(byte_array)
        offsets = [0] * len(self.ik_chains)
        for idx, ik_chain in enumerate(self.ik_chains):
            offsets[idx] = len(byte_array) + (len(offsets) * 4)

            byte_array.extend(ik_chain.to_binary())

        for offset in offsets:
            header_byte_array.extend(u32(offset).to_binary())
        return header_byte_array + byte_array


    def add_slot_assignment(self, chain_idx, target_actor, target_bone):
        if chain_idx + 1 > len(self.ik_chains):
            chains_to_add = (chain_idx + 1) - len(self.ik_chains)
            print(chains_to_add)
            for i in range(chains_to_add):
                self.ik_chains.append(SlotAssignmentIKChainTS3([]))
        self.ik_chains[chain_idx].slot_assignments.append(SlotAssignmentTS3(len(self.ik_chains[chain_idx].slot_assignments), target_actor, target_bone))