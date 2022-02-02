from _s4animtools.serialization.types.basic import UInt16
from _s4animtools.frames.frame import Frame

class TranslationFrame(Frame):
    def set_frame_data(self, startTick, frame_data, snap_frame):
        self._startTick = UInt16(startTick)
        sign_bits = [frame_data[0] < 0, frame_data[1] < 0, frame_data[2] < 0, 0,
                     0, 0, 0, snap_frame]
        sign_bits = [str(int(x)) for x in sign_bits]
        # Flip the sign bits for endianness
        sign_bits = "".join(sign_bits)[::-1]

        #print(sign_bits)
        self._sign_bits = UInt16(int(sign_bits, 2))
        self._frame_data = frame_data

    def serialize(self):
        serialize_order = [self._startTick, self._sign_bits]
        frame_data = []
        for item in serialize_order:
            frame_data.append(item.serialize())
        for data in self._frame_data:
            frame_data.append(data.serialize())
        return frame_data
