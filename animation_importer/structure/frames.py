from S4ClipThing.structure.channel_type import ChannelType
from S4ClipThing.types.basic import uint32, float32, uint16, byte, intByte
from S4ClipThing.structure.channel_width import GetWidthForChannelType, GetCountForChannelType


class Frame:
    def __str__(self):
        return "{}".format(vars(self))

    def __repr__(self):
        return "{}".format(vars(self))

    # Start tick must be greater than last start tick
    # Start tick must be between 0 and frame end.

    def deserialize(self, data, channelType, offset, scale, last_tick):
        self.startTick = uint16.deserialize(data)
        if last_tick > self.startTick:
            print(last_tick, self.startTick, data.tell())
            raise Exception("Start tick must be greater than last start tick")

        sign_bits = uint16.deserialize(data)
        self.sign_bits = sign_bits >> 4

        channel_width = GetWidthForChannelType(channelType)
        entry_count = GetCountForChannelType(channelType)
        pad = 0

        self.indices = []
        self.padding = []
        self.values = []

        if channel_width == 2:
            for chunk in range(entry_count):
                if channelType == ChannelType.F4_SuperHighPrecision_Quaternion:
                    axis_val = uint16.deserialize(data)

                    max_val = 4095
                    masked_val = axis_val / max_val
                    if sign_bits & 1 << chunk:
                        masked_val *= -1
                else:
                    masked_val = uint16.deserialize(data)
                    max_val = 65535
                    # Sign bits for actual animation data, not the indices
                    #if sign_bits & 1 << chunk:
                    #    masked_val *= -1
                masked_val *= scale
                masked_val += offset
                self.values.append(masked_val)
        else:
            if channel_width == 4:
                val = uint32.deserialize(data)
                for entry in range(3):
                    bits_per_float = 10
                    max_val = 1023
                    mask = max_val << (entry * bits_per_float)
                    axis_val = ((val & mask) >> (entry * bits_per_float)) / max_val
                    if sign_bits & 1 << entry:
                        axis_val *= -1

                    axis_val *= scale
                    axis_val += offset
                    self.values.append(axis_val)
                if channel_width == 1:
                    val = intByte.deserialize(data)
                    if sign_bits & 1:
                        val *= -1

                    val *= scale
                    val += offset
                    self.values.append(val)


        if channel_width == 2:
            pad = 0
        elif channel_width == 1:
            pad = 4 - entry_count

        print("pos", data.tell())
        print("pad", pad)


        if pad > 0:
            for i in range(pad):
                self.padding.append(byte.deserialize(data, 1))
        #print(self.values, channel_width, entry_count)
        #print(vars(self))
        return self