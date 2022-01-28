import importlib
import _s4animtools.frames.frame

import _s4animtools.clip_processing.value_types
from _s4animtools.clip_processing.value_types import uint16, uint32, float32, byte8
import _s4animtools.clip_processing.test_tool
import _s4animtools.channel

importlib.reload(_s4animtools.frames.frame)
importlib.reload(_s4animtools.clip_processing.value_types)


class F1Normalized(_s4animtools.channel.Channel):
    def serialize_data(self, value):
        return _s4animtools.clip_processing.serializable_bytes(byte8(value).serialize() + byte8(0).serialize())

    def compress_data(self, value):
        # F1 Normalized data uses 8 bits of data
        return int(round(abs(value * 255)))

    def set_channel_data(self, offset, scale, individual_frames, snap_frames):
        self._offset = offset
        self._scale = scale
        self._individual_frames = individual_frames
        self._frame_count = len(self._individual_frames)

        for idx, values in self._individual_frames.items():
            single_frame = _s4animtools.f1_normalized_frame.F1NormalizedFrame()
            single_frame.set_frame_data(idx, self.normalize_offset_scale(values), idx in snap_frames)
            single_frame._frame_data = self.compress_data(single_frame._frame_data)

            single_frame._frame_data = self.serialize_data(single_frame._frame_data)

            self.serialized_frames[idx] = single_frame

    def serialize(self):

        order = [uint32(self._data_offset), self._target, float32(self._offset), float32(self._scale), uint16(self._frame_count), byte8(self._channel_type ), byte8(self._sub_type)]
        serialized_header = []
        serialized_frames = []

        for item in order:
            serialized_header.append(item.serialize())

        for idx, frame in self.serialized_frames.items():
            serialized_frames.append(frame.serialize())

        return serialized_header, serialized_frames
