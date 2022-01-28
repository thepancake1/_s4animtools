from _s4animtools.clip_processing.value_types import uint32, float32, serializable_string, uint16, byte8
from _s4animtools.clip_processing.test_tool import get_size


class ClipBody:
    def __init__(self, clipname, source_file_name):
        # Current version number
        self._formatToken = "_pilC3S_"
        self._version = 2
        self._flags = 0
        self._tickLength = 1/30
        self._numTicks = 0
        self._padding = 0
        self._channel_count = 0
        self._f1PaletteSize = 0
        self._channelDataOffset = 48
        self._f1DataPaletteOffset = 0
        self._sourceNameOffset = 0
        self._sourceAssetNameOffset = 0
        self._clipName = clipname.encode("ascii") + byte8(0).serialize()
        self._channels = []
        self._f1PaletteData = []
        self._source_file_name = source_file_name.encode("ascii") + byte8(0).serialize()

    def add_channel(self, new_channel):
        self._channel_count += 1
        self._channels.append(new_channel)

    def set_clip_length(self, length):
        self._numTicks = length

    def serialize(self):
        serialized = [serializable_string(self._formatToken), uint32(self._version),
                    uint32(self._flags), float32(self._tickLength), uint16(self._numTicks),
                    uint16(self._padding), uint32(self._channel_count), uint32(self._f1PaletteSize),
                    uint32(self._channelDataOffset), uint32(self._f1DataPaletteOffset), uint32(self._sourceNameOffset),
                      uint32(self._sourceAssetNameOffset)]

        serialized_channels = []
        raw_channel_data = []
        channel_offsets = {}
        data_offset = 48 # data offset starts at 48 for start of clip header



        for channel in self._channels:
            # Serialize the channels to get their sizes
           # print(data_offset)

            header, data = channel.serialize()
           # print(header,  get_size(header))
            data_offset += get_size(header)
            serialized_channels.append((header, data))
            raw_channel_data.append(header)


        # Set the offset values to their correct values
        serialized[-2] = uint32(data_offset)
        raw_channel_data.append(self._source_file_name)
        data_offset += len(self._source_file_name)
        serialized[-1] = uint32(data_offset)
        raw_channel_data.append(self._source_file_name)
        data_offset += len(self._source_file_name)
        serialized[-3] = uint32(data_offset)

        for data in self._f1PaletteData:
            # Assume data to be 4 bytes
            data_offset += 4
            raw_channel_data.append(data.serialize())

        # No actual f1 palette data currently
        # Append frame data
        for idx in range(len(serialized_channels)):
            channel_offsets[idx] = data_offset
           # print(data_offset)
            data = serialized_channels[idx][1]
           # print(data, get_size(data))

            raw_channel_data.append(data)
            data_offset += get_size(data)
        # Note, clip name and source name are stored between clip channel headers and actual clip data
        for idx in range(len(serialized_channels)):

            # Update the channel data offset to its actual offset
            raw_channel_data[idx][0] = uint32(channel_offsets[idx]).serialize()

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.serialize())

        return serialized_stuff, raw_channel_data
