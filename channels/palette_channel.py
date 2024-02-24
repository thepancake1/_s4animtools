import importlib
import _s4animtools.frames.palette_frame
from _s4animtools.serialization.types.basic import UInt16, UInt32, Float32, Byte
import _s4animtools.serialization
import _s4animtools.channels.quaternion_channel
import _s4animtools.frames
from _s4animtools.frames.frame import PaletteFrame, PaletteTranslationFrame

importlib.reload(_s4animtools.channels.quaternion_channel)
importlib.reload(_s4animtools.frames.palette_frame)
class PaletteQuaternionChannel(_s4animtools.channels.quaternion_channel.QuaternionChannel):
    def serialize_data(self, value):
        return UInt16(value)

    def quantize_data(self, value):
        return

    def palette_setup(self, channel_data, snap_frames=None, values=None):
        if snap_frames is None:
            snap_frames = []
        channel_frame_values = {}
        for idx, frame_data in channel_data.items():
            channel_frame_values[idx] = frame_data.copy()
        self.set_channel_data(offset=0, scale=1, individual_frames=channel_frame_values,
                                         snap_frames=snap_frames, actual_values=values)

    def set_channel_data(self, offset, scale, individual_frames, snap_frames, actual_values):
        self._offset = 0
        self._scale = 1
        self._individual_frames = individual_frames
        self._frame_count = len(self._individual_frames)

        for idx, values in self._individual_frames.items():
            single_frame = PaletteFrame()
            single_frame.set_frame_data(idx, list(values), idx == 0, actual_values[idx])
            single_frame._frame_data = list(map(self.serialize_data, single_frame._frame_data))
            serialized = single_frame._frame_data
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

class PaletteTranslationChannel(PaletteQuaternionChannel):
    def serialize_data(self, value):
        return UInt16(value)

    def quantize_data(self, value):
        return

    def set_channel_data(self, offset, scale, individual_frames, snap_frames, actual_values):
        self._offset = 0
        self._scale = 1
        self._individual_frames = individual_frames
        self._frame_count = len(self._individual_frames)

        for idx, values in self._individual_frames.items():
            single_frame = PaletteTranslationFrame()
            single_frame.set_frame_data(idx, list(values), idx == 0, actual_values[idx])
            single_frame._frame_data = list(map(self.serialize_data, single_frame._frame_data))
            serialized = single_frame._frame_data
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



