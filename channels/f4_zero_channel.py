import importlib
import _s4animtools.frames.frame
import _s4animtools.channels.channel

importlib.reload(_s4animtools.frames.frame)

class F4ZeroChannel(_s4animtools.channels.channel.QuaternionChannel):
    def set_channel_data(self, offset, scale, individual_frames, snap_frames):
        self._offset = offset
        self._scale = scale
