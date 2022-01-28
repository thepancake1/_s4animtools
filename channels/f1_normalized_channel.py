import importlib
import _s4animtools.frames.f1_normalized_frame
from _s4animtools.serialization.types.basic import UInt16, UInt32, Float32, Byte, Bytes
import _s4animtools.serialization


class F1Normalized(_s4animtools.channel.Channel):
    def serialize_data(self, value):
        return Bytes(Byte(value).serialize() + Byte(0).serialize())

    def quantize_data(self, value):
        # F1 Normalized data uses 8 bits of data
        return int(round(abs(value * 255)))

    def set_channel_data(self, offset, scale, individual_frames, snap_frames=[]):
        self._offset = offset
        self._scale = scale
        self._individual_frames = individual_frames
        self._frame_count = len(self._individual_frames)

        for idx, values in self._individual_frames.items():
            #print("Original Value: {}, Idx: {}".format(values, idx))
            single_frame = _s4animtools.frames.f1_normalized_frame.F1NormalizedFrame()
            single_frame.set_frame_data(idx, self.normalize_offset_scale(values), idx in snap_frames)
            single_frame._frame_data = self.quantize_data(single_frame._frame_data)
            #print(single_frame._frame_data)
            single_frame._frame_data = self.serialize_data(single_frame._frame_data)

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
