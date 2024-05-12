import importlib
import s4animtools.frames.f1_normalized_frame
from s4animtools.serialization.types.basic import UInt16, UInt32, Float32, Byte, Bytes
import s4animtools.serialization
import s4animtools.channels.quaternion_channel
import math

class F1Normalized(s4animtools.channels.quaternion_channel.QuaternionChannel):
    def serialize_data(self, value):
        return Bytes(Byte(value).serialize() + Byte(0).serialize())

    def quantize_data(self, value):
        # F1 Normalized data uses 8 bits of data
        return int(math.floor(abs(value * 255)))

    def set_channel_data(self, offset, scale, individual_frames, snap_frames=[]):
        self._offset = offset
        self._scale = scale
        self._individual_frames = individual_frames
        self._frame_count = len(self._individual_frames)

        for idx, values in self._individual_frames.items():
            single_frame = s4animtools.frames.f1_normalized_frame.F1NormalizedFrame()
            single_frame.set_frame_data(idx, self.normalize_offset_scale(values), idx in snap_frames)
            single_frame._frame_data = self.quantize_data(single_frame._frame_data)
            single_frame._frame_data = self.serialize_data(single_frame._frame_data)

            self.serialized_frames[idx] = single_frame

    def serialize(self):

        serialize_order = [UInt32(self._data_offset), self._target, Float32(self._offset), Float32(self._scale), UInt16(self._frame_count), Byte(self._channel_type), Byte(self._sub_type)]
        serialized_header = []
        serialized_frames = []

        for item in serialize_order:
            serialized_header.append(item.serialize())

        for idx, frame in self.serialized_frames.items():
            serialized_frames.append(frame.serialize())

        return serialized_header, serialized_frames
