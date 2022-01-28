import importlib
import _s4animtools.frames.frame

import _s4animtools.clip_processing.value_types
import _s4animtools.channel

importlib.reload(_s4animtools.frames.frame)
importlib.reload(_s4animtools.clip_processing.value_types)

class F4ZeroChannel(_s4animtools.channel.Channel):
    def set_channel_data(self, offset, scale, individual_frames, snap_frames):
        self._offset = offset
        self._scale = scale
