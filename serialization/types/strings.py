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
        return u32(len(self.string)).serialize() + self.string.encode("ascii")
