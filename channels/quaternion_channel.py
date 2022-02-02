import importlib
import _s4animtools.frames.frame
from _s4animtools.serialization.types.basic import UInt16, UInt32, Float32, Byte
import _s4animtools.serialization
from _s4animtools.serialization.fnv import get_32bit_hash
import math
importlib.reload(_s4animtools.frames.frame)


class QuaternionChannel:
    def __init__(self, channel_name, channel_type, sub_type):
        self._channel_name = channel_name
        self._target = UInt32(get_32bit_hash(channel_name))
        self._data_offset = 0
        self._offset = 0
        self._scale = 0
        self._frame_count = 0
        self._individual_frames = {}
        self.serialized_frames = {}
        self._channel_type = channel_type
        self._sub_type = sub_type

    def normalize_offset_scale(self, value):
        if self._scale == 0:
            self._scale = 1
        return (value - self._offset) / self._scale

    def serialize_data(self, value):
        return UInt16(value)

    def quantize_data(self, value):
        # Throw away the sign. Watch it burn.
        # Rotation data uses 12 bits of precision
        return int(math.floor(abs(value * 4095)))

    def setup(self, channel_data, snap_frames=None):
        if snap_frames is None:
            snap_frames = []
        channel_frame_values = {}
        min, max = 9999, -9999
        for idx, frame_data in channel_data.items():
            channel_frame_values[idx] = frame_data.copy()
            for value in frame_data:
                if max < value:
                    max = value
                if min > value:
                    min = value
        offset = (min + max) / 2
        scale = -((min - max) / 2)
        self.set_channel_data(offset=offset, scale=scale, individual_frames=channel_frame_values,
                                         snap_frames=snap_frames)

    def set_channel_data(self, offset, scale, individual_frames, snap_frames):
        self._offset = offset
        self._scale = scale
        self._individual_frames = individual_frames
        self._frame_count = len(self._individual_frames)
        for idx, values in self._individual_frames.items():
            values = (values[1], values[2], values[3], values[0])
            single_frame = _s4animtools.frames.frame.Frame()
            single_frame.set_frame_data(idx, list(map(self.normalize_offset_scale, values)), idx in snap_frames)
            single_frame._frame_data = list(map(self.quantize_data, single_frame._frame_data))
            single_frame._frame_data = list(map(self.serialize_data, single_frame._frame_data))
            self.serialized_frames[idx] = single_frame

    def serialize(self):

        order = [UInt32(self._data_offset), self._target, Float32(self._offset), Float32(self._scale),
                 UInt16(self._frame_count), Byte(self._channel_type), Byte(self._sub_type)]
        serialized_header = []
        serialized_frames = []

        for item in order:
            serialized_header.append(item.serialize())
        for idx, frame in self.serialized_frames.items():
            serialized_frames.append(frame.serialize())

        return serialized_header, serialized_frames
