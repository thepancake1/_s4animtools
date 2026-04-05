from s4animtools.serialization.types.basic import u32, String
from s4animtools.serialization import Serializable


class Byte512String(Serializable):
    def __init__(self, string):
        self.string = string

    @staticmethod
    def from_binary(reader):
        value = reader.read(512).split("#")[0]
        return Byte512String(value)

    def to_binary(self):
        encoded_string = self.string.encode("ascii") + bytearray([0x00])
        b = bytearray(encoded_string)
        b.extend([0x23] * (512 - len(encoded_string)))
        return b

class IOString(Serializable):
    def __init__(self, string):
        self.string = string

    @staticmethod
    def from_binary(reader):
        length = reader.u32()
        value = reader.read_string(length)
        return IOString(value)

    def to_binary(self):
        return u32(len(self.string)).to_binary() + self.string.encode("ascii")

class NullTerminatedString(Serializable):
    def __init__(self, string):
        self.string = string

    @staticmethod
    def from_binary(reader):
        current_char = reader.read(1)
        value = bytearray([current_char])
        while current_char != b'\x00':
            current_char = reader.read(1)
            value.append(current_char)
        # Convert bytearray to string, stripping the null terminator
        return NullTerminatedString(value.decode("ascii").rstrip('\x00'))

    def to_binary(self):
        return self.string.encode("ascii") + b'\x00'