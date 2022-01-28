from _s4animtools.serialization.types.basic import UInt32, UInt16
import _s4animtools.clip_processing
import importlib

importlib.reload(_s4animtools.clip_processing.clip_body)


class SlotAssignment:
    def __init__(self, chainIdx, slotIdx, actor, target):
        self._chainIdx = chainIdx
        self._slotIdx = slotIdx
        self._actor = actor
        self._target = target


    def serialize(self):
        return [UInt16(self._chainIdx).serialize(), UInt16(self._slotIdx).serialize(), UInt32(len(self._actor)).serialize(),
                self._actor, UInt32(len(self._target)).serialize(), self._target]
