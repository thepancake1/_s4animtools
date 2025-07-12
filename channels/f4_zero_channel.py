import importlib
import s4animtools.frames.frame
import s4animtools.channels.quaternion_channel

class F4ZeroChannel(s4animtools.channels.quaternion_channel.QuaternionChannel):
    def set_channel_data(self, offset, scale, individual_frames, snap_frames):
        self._offset = offset
        self._scale = scale
