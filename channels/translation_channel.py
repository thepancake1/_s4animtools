import importlib
import s4animtools.frames.translation_frame
from s4animtools.serialization.types.basic import u16, u32, f32, u8
import s4animtools.serialization
import s4animtools.channels.quaternion_channel
import math
from s4animtools.channels.palette_channel import PaletteTranslationChannel
importlib.reload(s4animtools.channels.quaternion_channel)
importlib.reload(s4animtools.frames.translation_frame)
class Vector3Channel(s4animtools.channels.quaternion_channel.QuaternionChannel):
    def serialize_data(self, value):
        return u16(value)

    def quantize_data(self, value):
        # Throw away the sign. Watch it burn.
        # Rotation data uses 10 bits of precision
        return int(math.floor(abs(value * 1023)))

    def set_channel_data(self, offset, scale, individual_frames, snap_frames):
        self._offset = offset
        self._scale = scale
        self._individual_frames = individual_frames
        self._frame_count = len(self._individual_frames)

        for idx, values in self._individual_frames.items():
            single_frame = s4animtools.frames.translation_frame.TranslationFrame()
            single_frame.set_frame_data(idx, list(map(self.normalize_offset_scale, values)), idx in snap_frames)
            single_frame._frame_data = list(map(self.quantize_data, single_frame._frame_data))
            single_frame._frame_data = list(map(self.serialize_data, single_frame._frame_data))
            serialized = single_frame._frame_data
            combined_bits = serialized[0].data + (serialized[1].data << 10) + (serialized[2].data << 20)
            single_frame._bitshifted_data = u32(combined_bits)
            self.serialized_frames[idx] = single_frame

    def serialize(self):

        serialize_order = [u32(self._data_offset), self._target, f32(self._offset), f32(self._scale), u16(self._frame_count), u8(self._channel_type), u8(self._sub_type)]
        serialized_header = []
        serialized_frames = []

        for item in serialize_order:
            serialized_header.append(item.to_binary())
        for idx, frame in self.serialized_frames.items():
            serialized_frames.append(frame.to_binary())

        return serialized_header, serialized_frames
