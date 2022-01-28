from _s4animtools.serialization.types.basic import UInt16
from _s4animtools.frames.frame import Frame

class F1NormalizedFrame(Frame):
    def set_frame_data(self, startTick, value, snap_frame):
        """Set frame data for F1 Normalized Frame.
        This is slightly different as there is only
        one value in the animation data nd sign bits."""
        self._startTick = UInt16(startTick)
        sign_bits = [value, 0, 0, 0,
                     0, 0, 0, snap_frame]
        sign_bits = [str(int(x)) for x in sign_bits]

        self._sign_bits = UInt16(int(value < 0))
        self._frame_data = value


    def serialize(self):
        """This function serializes the data somewhat differently as
        it frame data is a single value.
        Returns a serialized version of the frame data.
        """
        serialize_order = [self._startTick, self._sign_bits]
        frame_data = []
        for item in serialize_order:
            frame_data.append(item.serialize())
        frame_data.append(self._frame_data.serialize())
        return frame_data
