from collections import namedtuple

from s4animtools.channels.quaternion_channel import QuaternionChannel
from s4animtools.channels.translation_channel import Vector3Channel
from s4animtools.serialization.types.basic import u32, f32, String, u16, u8
from s4animtools.serialization import get_size
from s4animtools.serialization.types.strings import NullTerminatedString

OFFSET_TO_CHANNEL_DATA = 48
SerializedChannel = namedtuple('SerializedChannel', ['header', 'data'])

class ClipBody:
    def __init__(self, clipname, source_file_name, version=2, flags = 0, tick_length = 1/30, num_ticks= 0, padding=0, f1_palette=None, f1_data_palette_offset=0,
                 channel_data_offset=OFFSET_TO_CHANNEL_DATA, clip_name_offset=0, source_asset_name_offset=0):
        """ Current version number"""

        self._formatToken = "_pilC3S_"
        self._version = version
        self._flags = flags
        self._tickLength = tick_length
        self._numTicks = num_ticks
        self._padding = padding
        self._f1PaletteSize:int = 0
        if f1_palette is not None:
            self._f1PaletteSize = len(f1_palette)
        self._channelDataOffset:int = channel_data_offset
        self._f1DataPaletteOffset:int = f1_data_palette_offset
        self._clipNameOffset:int = clip_name_offset
        self._sourceAssetNameOffset: int = source_asset_name_offset

        self._clipName:str = clipname
        self._channels : list[QuaternionChannel] = []
        if f1_palette is None:
            self._f1PaletteData = []
        else:
            self._f1PaletteData = f1_palette
        self._source_file_name = source_file_name

    def add_channel(self, new_channel : QuaternionChannel):
        """
        Adds a new channel to the clip body
        """
        self._channels.append(new_channel)
    @property
    def channel_count(self):
        return len(self._channels)

    def set_palette_values(self, palette_values):
        self._f1PaletteData = list(map(f32, map(abs, palette_values)))

    def set_clip_length(self, length):
        """
        Sets the clip length in ticks
        """
        self._numTicks = length

    @property
    def clip_name_offset(self):
        data_offset = OFFSET_TO_CHANNEL_DATA
        for channel in self._channels:
            header, _ = channel.to_binary()
            data_offset += sum([len(item) for item in header])
        return data_offset

    @property
    def source_asset_name_offset(self):
        return self.clip_name_offset + len(self._clipName)

    @property
    def f1_palette_offset(self):
        return self.source_asset_name_offset + len(self._source_file_name)

    def to_binary(self):

        serialized = list()
        serialized.append(self._formatToken.encode('ascii'))
        serialized.append(u32(self._version).to_binary())
        serialized.append(u32(self._flags).to_binary())
        serialized.append(f32(self._tickLength).to_binary())
        serialized.append(u16(self._numTicks).to_binary())
        serialized.append(u16(self._padding).to_binary())
        serialized.append(u32(self.channel_count).to_binary())
        serialized.append(u32(self._f1PaletteSize).to_binary())
        serialized.append(u32(self._channelDataOffset).to_binary())
        serialized.append(u32(self.f1_palette_offset).to_binary())
        serialized.append(u32(self.clip_name_offset).to_binary())
        serialized.append(u32(self.source_asset_name_offset).to_binary())
        serialized_channels:list[SerializedChannel] = []
        clip_body_data = []
        channel_offsets = {}
        # Offset from header
        data_offset = OFFSET_TO_CHANNEL_DATA


        """
        Serialize the channels then add the channel data to the serialize_order data. 
        It also updates the channel offsets to point to the correct location in the serialize_order data.
        """
        for channel in self._channels:
            #print(type(channel))
            header, data = channel.to_binary()
            data_offset += sum([len(item) for item in header])
            print(data_offset)
            serialized_channels.append(SerializedChannel(header, data))
            clip_body_data.append(header)

        # Clip name is a null-terminated string
        clip_name_encoded = NullTerminatedString(self._clipName).to_binary()
        clip_body_data.append(clip_name_encoded)
        data_offset += len(clip_name_encoded)
        source_file_name_encoded = NullTerminatedString(self._source_file_name).to_binary()

        clip_body_data.append(source_file_name_encoded)
        data_offset += len(source_file_name_encoded)

        for idx, data in enumerate(self._f1PaletteData):
            data_offset += 4
            clip_body_data.append(data.to_binary())
            #print(idx, data.value)


        for idx in range(self.channel_count):
            #print(serialized_channels[idx])
            all_channel_data = b""
            channel_offsets[idx] = data_offset
            for frame in serialized_channels[idx].data:
                channel_data = b"".join(frame)
                all_channel_data += channel_data

            clip_body_data.append(all_channel_data)
            data_offset += len(all_channel_data)
        for idx in range(self.channel_count):
            clip_body_data[idx][0] = u32(channel_offsets[idx]).to_binary()

        serialized_bytes = bytearray()
        for idx, item in enumerate([*serialized, *clip_body_data]):
           # print(idx, item)
            if isinstance(item, bytes):
                serialized_bytes.extend(item)
            elif isinstance(item, list):
                for subitem in item:
                    if isinstance(subitem, bytes):
                        serialized_bytes.extend(subitem)
                    else:
                        raise TypeError(f"Expected bytes in subitem, got {type(subitem)}")
            else:
                raise TypeError(f"Expected bytes, got {type(item)}")
        return serialized_bytes

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

