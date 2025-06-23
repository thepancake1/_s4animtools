from s4animtools.serialization.types.basic import u32, String
from s4animtools.serialization import Serializable

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