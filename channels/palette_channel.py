import importlib
import _s4animtools.frames.palette_frame
import _s4animtools.clip_processing.value_types
from _s4animtools.clip_processing.value_types import uint16, uint32, float32, byte8
import _s4animtools.clip_processing.test_tool
import _s4animtools.channel
importlib.reload(_s4animtools.channel)
importlib.reload(_s4animtools.frames.palette_frame)
importlib.reload(_s4animtools.clip_processing.value_types)
class PaletteChannel(_s4animtools.channel.Channel):
    def serialize_data(self, value):
        return uint16(value)

    def compress_data(self, value):
        return

    def set_channel_data(self, offset, scale, individual_frames, snap_frames):
        self._offset = offset
        self._scale = scale
        self._individual_frames = individual_frames
        self._frame_count = len(self._individual_frames)

        for idx, values in self._individual_frames.items():
            single_frame = _s4animtools.frames.palette_frame.PaletteFrame()
            single_frame.set_frame_data(idx, list(values), idx == 0)
            single_frame._frame_data = list(map(self.serialize_data, single_frame._frame_data))
            serialized = single_frame._frame_data
            #print(combined_bits)
            #print(idx, self._individual_frames[idx])
            self.serialized_frames[idx] = single_frame

    def serialize(self):

        order = [uint32(self._data_offset), self._target, float32(self._offset), float32(self._scale), uint16(self._frame_count), byte8(self._channel_type), byte8(self._sub_type)]
        serialized_header = []
        serialized_frames = []

        for item in order:
            serialized_header.append(item.serialize())
        for idx, frame in self.serialized_frames.items():
            serialized_frames.append(frame.serialize())

        return serialized_header, serialized_frames

