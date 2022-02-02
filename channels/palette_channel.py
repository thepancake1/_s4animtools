import importlib
import _s4animtools.frames.palette_frame
from _s4animtools.serialization.types.basic import UInt16, UInt32, Float32, Byte
import _s4animtools.serialization
import _s4animtools.channels.quaternion_channel
importlib.reload(_s4animtools.channels.quaternion_channel)
importlib.reload(_s4animtools.frames.palette_frame)
class PaletteChannel(_s4animtools.channels.quaternion_channel.QuaternionChannel):
    def serialize_data(self, value):
        return UInt16(value)

    def quantize_data(self, value):
        return

    def set_channel_data(self, offset, scale, individual_frames, snap_frames):
        self._offset = 0
        self._scale = 1
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

        order = [UInt32(self._data_offset), self._target, Float32(self._offset), Float32(self._scale), UInt16(self._frame_count), Byte(self._channel_type), Byte(self._sub_type)]
        serialized_header = []
        serialized_frames = []

        for item in order:
            serialized_header.append(item.serialize())
        for idx, frame in self.serialized_frames.items():
            serialized_frames.append(frame.serialize())

        return serialized_header, serialized_frames

