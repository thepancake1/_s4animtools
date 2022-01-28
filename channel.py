import importlib
import _s4animtools.frames.frame

import _s4animtools.clip_processing.value_types
from _s4animtools.clip_processing.value_types import uint16, uint32, float32, byte8
import _s4animtools.clip_processing.test_tool

importlib.reload(_s4animtools.frames.frame)
importlib.reload(_s4animtools.clip_processing.value_types)
class Channel:
    def __init__(self, channel_name, channel_type, sub_type):
        self._channel_name = channel_name
        self._target = uint32(_s4animtools.clip_processing.test_tool.get_hash_from_bone_name(channel_name))
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
        return uint16(value)

    def compress_data(self, value):
        # Throw away the sign. Watch it burn.
        # Rotation data uses 32 bits of precision
        return int(round(abs(value * 4095)))

    def setup(self, channel_data):
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
                                         snap_frames=[])

    def set_channel_data(self, offset, scale, individual_frames, snap_frames):
        self._offset = offset
        self._scale = scale
        self._individual_frames = individual_frames
        self._frame_count = len(self._individual_frames)
        for idx, values in self._individual_frames.items():
            single_frame = _s4animtools.frames.frame.Frame()
            single_frame.set_frame_data(idx, list(map(self.normalize_offset_scale, values)), idx in snap_frames)
            single_frame._frame_data = list(map(self.compress_data, single_frame._frame_data))
            single_frame._frame_data = list(map(self.serialize_data, single_frame._frame_data))
            #print(idx, self._individual_frames[idx])
            self.serialized_frames[idx] = single_frame

    def serialize(self):

        order = [uint32(self._data_offset), self._target, float32(self._offset), float32(self._scale), uint16(self._frame_count), byte8(self._channel_type ), byte8(self._sub_type)]
        serialized_header = []
        serialized_frames = []

        for item in order:
            serialized_header.append(item.serialize())
        for idx, frame in self.serialized_frames.items():
            serialized_frames.append(frame.serialize())

            # with open(anim_path + "\\{}-{}-{}-{}.channel".format(self._channel_name, "F4_SuperHighPrecision_Quaternion",
            #                                         "SubChannelType.Orientation", "Header"), "wb") as file:
            # for item in order:
            # #    file.write(item.serialize())

            # with open(anim_path + "\\{}-{}-{}-{}.channel".format(self._channel_name, "F4_SuperHighPrecision_Quaternion",
            #                                                  "SubChannelType.Orientation", "Body"), "wb") as file:


        return serialized_header, serialized_frames
