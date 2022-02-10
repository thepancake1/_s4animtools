from _s4animtools.serialization.types.basic import UInt16
from _s4animtools.frames.frame import Frame

class PaletteFrame(Frame):
    def set_frame_data(self, startTick, frame_data, snap_frame):
        """
        Set frame data for the Palette Frame.
        This is unlike the typical frame as the frame
        data consists of indices to the palette array.
        Due to that, these values are never negative or below zero.
        The sign bits are never set to anything than zero because of this.
        """
        self._startTick = UInt16(startTick)
        #print(sign_bits)
        if not snap_frame:
            self._sign_bits = UInt16(0)
        else:
            self._sign_bits = UInt16(16)
        self._frame_data = frame_data

    def serialize(self):
        serialize_order = [self._startTick, self._sign_bits, *self._frame_data]
        frame_data = []
        for item in serialize_order:
            frame_data.append(item.serialize())
        return frame_data
