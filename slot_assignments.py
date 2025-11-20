from s4animtools.serialization.types.basic import u32, u16
from s4animtools.serialization.types.strings import IOString


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

    # This doesn't match the new convention of to_binary having a writer which it writes to.
    def to_binary(self):
        return [u16(self._chain_idx).to_binary(),
                u16(self._slot_idx).to_binary(),
                IOString(self._actor).to_binary(),
                IOString(self._target).to_binary()]
