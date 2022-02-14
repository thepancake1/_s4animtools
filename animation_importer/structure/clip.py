from S4ClipThing.types.basic import uint32, float32, uint16
from S4ClipThing.structure.channel import Channel

class S4Clip:

    def deserialize(self, data, clip_name):
        self.startOffset = data.tell()
        self.formatToken1 = uint32.deserialize(data)
        self.formatToken2 = uint32.deserialize(data)

        self.version = uint32.deserialize(data)

        self.flags = uint32.deserialize(data)

        self.tickLength = float32.deserialize(data)
        self.numTicks = uint16.deserialize(data)
        self.padding = uint16.deserialize(data)
        self.channelCount = uint32.deserialize(data)

        self.f1PaletteSize = uint32.deserialize(data)
        self.channelDataOffset = uint32.deserialize(data)
        self.f1DataPaletteOffset = uint32.deserialize(data)
        self.nameOffset = uint32.deserialize(data)
        self.sourceAssetNameOffset = uint32.deserialize(data)
        self.channels = []
        channelOffset = self.startOffset + self.channelDataOffset
        if self.channelCount > 0:
            data.seek(self.startOffset + self.channelDataOffset, 0)
            for i in range(self.channelCount):
                print("Channel count ", i)
                self.channels.append(Channel().deserialize(data, self.startOffset + self.channelDataOffset))
        return self, self.channels