from s4animtools.serialization.types.basic import UInt32, UInt16
from s4animtools.serialization.types.strings import IOString


class SlotAssignment:
    def __init__(self, chainIdx, slotIdx, actor, target):
        self._chainIdx = chainIdx
        self._slotIdx = slotIdx
        self._actor = actor
        self._target = target

    @staticmethod
    def from_binary(reader):
        chain_idx = reader.u16()
        slot_idx = reader.u16()
        target_object_namespace = IOString.from_binary(reader)
        target_joint_name = IOString.from_binary(reader)

    def serialize(self):
        return [UInt16(self._chainIdx).serialize(), UInt16(self._slotIdx).serialize(), UInt32(len(self._actor)).serialize(),
                self._actor, UInt32(len(self._target)).serialize(), self._target]
