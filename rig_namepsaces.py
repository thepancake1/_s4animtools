from _s4animtools.clip_processing.value_types import uint32, uint16
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
        return [uint16(self._chainIdx).serialize(), uint16(self._slotIdx).serialize(), uint32(len(self._actor)).serialize(),
                self._actor, uint32(len(self._target)).serialize(), self._target]
