from _s4animtools.serialization.types.basic import UInt32, Float32, String, UInt16, Byte
from _s4animtools.serialization import get_size

# You will need to update this should serialize_order change
F1_PALETTE_SIZE = -5
CHANNEL_DATA_OFFSET = -4
F1_PALETTE_OFFSET = -3
CLIP_NAME_OFFSET_IDX = -2
SOURCE_ASSET_NAME_OFFSET_IDX = -1

OFFSET_TO_CHANNEL_DATA = 48


class ClipBody:
    def __init__(self, clipname, source_file_name):
        """ Current version number"""
        self._formatToken = "_pilC3S_"
        self._version = 2
        self._flags = 0
        self._tickLength = 1/30
        self._numTicks = 0
        self._padding = 0
        self._channel_count = 0
        self._f1PaletteSize = 0
        # Offset to the start of the channel data
        self._channelDataOffset = OFFSET_TO_CHANNEL_DATA
        # Offset to the start of the f1 palette data
        self._f1DataPaletteOffset = 0
        # Offset to the start of the clip name
        self._clipNameOffset = 0
        # Offset to the start of the source file name
        self._sourceAssetNameOffset = 0

        # Set the clip name by converting it to bytes using ascii encoding
        self._clipName = clipname.encode("ascii") + Byte(0).serialize()
        # Initialize channels
        self._channels = []
        # Initialize f1 palette data
        self._f1PaletteData = []
        # Set source file name
        self._source_file_name = source_file_name.encode("ascii") + Byte(0).serialize()

    def add_channel(self, new_channel):
        """
        Adds a new channel to the clip body and updates the channel count
        """
        self._channel_count += 1
        self._channels.append(new_channel)




    def set_palette_values(self, palette_values):
        self._f1PaletteData = list(map(Float32, map(abs,  palette_values)))
        #print(self._f1PaletteData[0].value)
    def set_clip_length(self, length):
        """
        Sets the clip length in ticks
        """
        self._numTicks = length

    def serialize(self):
        serialize_order = [String(self._formatToken), UInt32(self._version),
                      UInt32(self._flags), Float32(self._tickLength), UInt16(self._numTicks),
                      UInt16(self._padding), UInt32(self._channel_count), UInt32(self._f1PaletteSize),
                      UInt32(self._channelDataOffset), UInt32(self._f1DataPaletteOffset), UInt32(self._clipNameOffset),
                      UInt32(self._sourceAssetNameOffset)]

        serialized_channels = []
        clip_body_data = []
        channel_offsets = {}
        # Offset from header
        data_offset = OFFSET_TO_CHANNEL_DATA


        """
        Serialize the channels then add the channel data to the serialize_order data. 
        It also updates the channel offsets to point to the correct location in the serialize_order data.
        """
        for channel in self._channels:
            header, data = channel.serialize()
            data_offset += get_size(header)
            serialized_channels.append((header, data))
            clip_body_data.append(header)

        serialize_order[CLIP_NAME_OFFSET_IDX] = UInt32(data_offset)
        clip_body_data.append(self._clipName)
        data_offset += len(self._clipName)

        serialize_order[SOURCE_ASSET_NAME_OFFSET_IDX] = UInt32(data_offset)
        clip_body_data.append(self._source_file_name)
        data_offset += len(self._source_file_name)

        serialize_order[F1_PALETTE_OFFSET] = UInt32(data_offset)
        serialize_order[F1_PALETTE_SIZE] = UInt32(len(self._f1PaletteData))
        for idx, data in enumerate(self._f1PaletteData):
            data_offset += 4
            clip_body_data.append(data.serialize())
            #print(idx, data.value)


        for idx in range(len(serialized_channels)):
            channel_offsets[idx] = data_offset
            data = serialized_channels[idx][1]

            clip_body_data.append(data)
            data_offset += get_size(data)
        for idx in range(len(serialized_channels)):
            clip_body_data[idx][0] = UInt32(channel_offsets[idx]).serialize()

        serialized_stuff = []
        for value in serialize_order:
            serialized_stuff.append(value.serialize())

        return serialized_stuff, clip_body_data
