from _s4animtools.serialization.types.basic import UInt16


class Frame:
    def __init__(self):
        self._startTick = None
        self._sign_bits = None
        self._frame_data = None
    def set_frame_data(self, startTick, frame_data, snap_frame):
        """
        Set the animation data for this frame.
        :param startTick: The tick at which this frame starts.
        :param frame_data: The frame data.
        :param snap_frame: The frame for snaping
        """
        self._startTick = UInt16(startTick)
        sign_bits = [frame_data[0] < 0, frame_data[1] < 0, frame_data[2] < 0, frame_data[3] < 0,
                     0, 0, 0, snap_frame]
        sign_bits = [str(int(x)) for x in sign_bits]
        # Flip the sign bits for endianness
        sign_bits = "".join(sign_bits)[::-1]
        self._sign_bits = UInt16(int(sign_bits, 2))
        self._frame_data = frame_data

    def serialize(self):
        """Specifies the order the data is layout."""
        serialize_order = [self._startTick, self._sign_bits]
        frame_data = []
        for item in serialize_order:
            frame_data.append(item.serialize())
        for data in self._frame_data:
            frame_data.append(data.serialize())
        return frame_data

class PaletteFrame:
    def __init__(self):
        self._startTick = None
        self._sign_bits = None
        self._frame_data = None
    def set_frame_data(self, startTick, frame_data, snap_frame, original_values):
        """
        Set the animation data for this frame.
        :param startTick: The tick at which this frame starts.
        :param frame_data: The frame data.
        :param snap_frame: The frame for snaping
        """
        self._startTick = UInt16(startTick)
        sign_bits = [original_values[0] < 0, original_values[1] < 0, original_values[2] < 0, original_values[3] < 0,
                     0, 0, 0, snap_frame]
        sign_bits = [str(int(x)) for x in sign_bits]
        # Flip the sign bits for endianness
        sign_bits = "".join(sign_bits)[::-1]
        self._sign_bits = UInt16(int(sign_bits, 2))
        self._frame_data = frame_data

    def serialize(self):
        """Specifies the order the data is layout."""
        serialize_order = [self._startTick, self._sign_bits]
        frame_data = []
        for item in serialize_order:
            frame_data.append(item.serialize())
        for data in self._frame_data:
            frame_data.append(data.serialize())
        return frame_data


class PaletteTranslationFrame:
    def __init__(self):
        self._startTick = None
        self._sign_bits = None
        self._frame_data = None
    def set_frame_data(self, startTick, frame_data, snap_frame, original_values):
        """
        Set the animation data for this frame.
        :param startTick: The tick at which this frame starts.
        :param frame_data: The frame data.
        :param snap_frame: The frame for snaping
        """
        self._startTick = UInt16(startTick)
        sign_bits = [original_values[0] < 0, original_values[1] < 0, original_values[2] < 0, 0,
                     0, 0, 0, snap_frame]
        sign_bits = [str(int(x)) for x in sign_bits]
        # Flip the sign bits for endianness
        sign_bits = "".join(sign_bits)[::-1]
        self._sign_bits = UInt16(int(sign_bits, 2))
        self._frame_data = frame_data

    def serialize(self):
        """Specifies the order the data is layout."""
        serialize_order = [self._startTick, self._sign_bits]
        frame_data = []
        for item in serialize_order:
            frame_data.append(item.serialize())
        for data in self._frame_data:
            frame_data.append(data.serialize())
        return frame_data

if __name__ == "__main__":
    pass
    #frame = Frame()
    #frame.set_frame_data(1, [0.120406516, -0.031965576, 0.450546116, 0.884018481])
    #sign_bits_int = int.from_bytes(frame._sign_bits, byteorder=sys.byteorder)
    #print(bin(sign_bits_int), sign_bits_int)