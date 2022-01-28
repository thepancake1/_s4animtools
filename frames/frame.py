from _s4animtools.clip_processing.value_types import uint16


class Frame:
    def __init__(self):
        self._startTick = None
        self._sign_bits = None
        self._frame_data = None
    def set_frame_data(self, startTick, frame_data, snap_frame):
        """Set the animation data for this frame."""
        self._startTick = uint16(startTick)
        sign_bits = [frame_data[0] < 0, frame_data[1] < 0, frame_data[2] < 0, frame_data[3] < 0,
                     0, 0, 0, snap_frame]
        sign_bits = [str(int(x)) for x in sign_bits]
        # Flip the sign bits for endianness
        sign_bits = "".join(sign_bits)[::-1]
        self._sign_bits = uint16(int(sign_bits, 2))
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