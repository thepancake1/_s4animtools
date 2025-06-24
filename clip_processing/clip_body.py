from s4animtools.serialization.types.basic import u32, f32, String, u16, u8
from s4animtools.serialization import get_size
from s4animtools.serialization.types.strings import NullTerminatedString

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
        self._f1PaletteSize = 0
        # Offset to the start of the channel data
        self._channelDataOffset = OFFSET_TO_CHANNEL_DATA
        # Offset to the start of the f1 palette data
        self._f1DataPaletteOffset = 0
        # Offset to the start of the clip name
        self._clipNameOffset = 0
        # Offset to the start of the source file name
        self._sourceAssetNameOffset = 0

        self._clipName = clipname
        self._channels = []
        self._f1PaletteData = []
        self._source_file_name = source_file_name

    def add_channel(self, new_channel):
        """
        Adds a new channel to the clip body
        """
        self._channels.append(new_channel)
    @property
    def _channel_count(self):
        return len(self._channels)

    def set_palette_values(self, palette_values):
        self._f1PaletteData = list(map(f32, map(abs, palette_values)))

    def set_clip_length(self, length):
        """
        Sets the clip length in ticks
        """
        self._numTicks = length

    def to_binary(self):

    def to_binary(self):
        serialize_order = [String(self._formatToken), u32(self._version),
                           u32(self._flags), f32(self._tickLength), u16(self._numTicks),
                           u16(self._padding), u32(self._channel_count), u32(self._f1PaletteSize),
                           u32(self._channelDataOffset), u32(self._f1DataPaletteOffset), u32(self._clipNameOffset),
                           u32(self._sourceAssetNameOffset)]

        serialized_channels = []
        clip_body_data = bytearray()
        channel_offsets = {}
        # Offset from header
        data_offset = OFFSET_TO_CHANNEL_DATA


        """
        Serialize the channels then add the channel data to the serialize_order data. 
        It also updates the channel offsets to point to the correct location in the serialize_order data.
        """
        for channel in self._channels:
            header, data = channel.to_binary()
            data_offset += get_size(header)
            serialized_channels.append((header, data))
            clip_body_data += header

        serialize_order[CLIP_NAME_OFFSET_IDX] = u32(data_offset)
        # Clip name is a null-terminated string
        clip_body_data += self._clipName
        data_offset += len(self._clipName)

        serialize_order[SOURCE_ASSET_NAME_OFFSET_IDX] = u32(data_offset)
        clip_body_data.append(self._source_file_name)
        data_offset += len(self._source_file_name)

        serialize_order[F1_PALETTE_OFFSET] = u32(data_offset)
        serialize_order[F1_PALETTE_SIZE] = u32(len(self._f1PaletteData))
        for idx, data in enumerate(self._f1PaletteData):
            data_offset += 4
            clip_body_data.append(data.to_binary())
            #print(idx, data.value)


        for idx in range(len(serialized_channels)):
            channel_offsets[idx] = data_offset
            data = serialized_channels[idx][1]

            clip_body_data.append(data)
            data_offset += get_size(data)
        for idx in range(len(serialized_channels)):
            clip_body_data[idx][0] = u32(channel_offsets[idx]).to_binary()

        serialized_bytes = bytearray()
        for value in serialize_order:
            serialized_bytes += value.to_binary()

        return serialized_bytes, clip_body_data

    @staticmethod
    def from_binary(reader):
        format_token = reader.read(8)
        if format_token != b"_pilC3S_":
            raise ValueError("Invalid format token")
        version = u32.from_binary(reader)
        if version != 2:
            raise ValueError(f"Unsupported version: {version}")
        flags = u32.from_binary(reader)
        tick_length = f32.from_binary(reader)
        num_ticks = u16.from_binary(reader)
        padding = u16.from_binary(reader)
        channel_count = u32.from_binary(reader)
        f1_palette_size = u32.from_binary(reader)

        channel_data_offset = u32.from_binary(reader)
        f1_palette_offset = u32.from_binary(reader)
        name_offset = u32.from_binary(reader)
        source_asset_name_offset = u32.from_binary(reader)

        current_pos = reader.tell()
        reader.seek(current_pos+name_offset, 0)
        clip_name = NullTerminatedString.from_binary(reader).string

