import importlib
import _s4animtools.frames.translation_frame
from _s4animtools.serialization.types.basic import UInt16, UInt32, Float32, Byte
import _s4animtools.serialization
import _s4animtools.channels.channel
importlib.reload(_s4animtools.channels.channel)
importlib.reload(_s4animtools.frames.translation_frame)
class Vector3Channel(_s4animtools.channels.channel.QuaternionChannel):
    def serialize_data(self, value):
        return UInt16(value)

    def quantize_data(self, value):
        # Throw away the sign. Watch it burn.
        # Rotation data uses 10 bits of precision
        return int(round(abs(value * 1023)))

    def set_channel_data(self, offset, scale, individual_frames, snap_frames):
        self._offset = offset
        self._scale = scale
        self._individual_frames = individual_frames
        self._frame_count = len(self._individual_frames)

        for idx, values in self._individual_frames.items():
            single_frame = _s4animtools.frames.translation_frame.TranslationFrame()
            single_frame.set_frame_data(idx, list(map(self.normalize_offset_scale, values)), idx in snap_frames)
            single_frame._frame_data = list(map(self.quantize_data, single_frame._frame_data))
           # list(map(print, single_frame._frame_data))
            single_frame._frame_data = list(map(self.serialize_data, single_frame._frame_data))
            serialized = single_frame._frame_data
            combined_bits = serialized[0].value + (serialized[1].value << 10) + (serialized[2].value << 20)
            single_frame._bitshifted_data = UInt32(combined_bits)
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

if __name__ == "__main__":
    channel = Vector3Channel("b__R_Squint__")
    channel.set_channel_data(0.444224, -0.570586, {0: [0.00024896969696969196,1.007001393939394,0.00024896969696969196]})
    data = channel.serialized_frames[0]._frame_data
    #print(data)