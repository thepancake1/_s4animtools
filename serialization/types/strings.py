from _s4animtools.serialization.types.basic import UInt32, String
from _s4animtools.serialization import Serializable

"""
Transform Types are types used for representing exported data 
that build on top on the Basic types but are used for things 
like a Vector3 or a Quaternion.
"""


class ASCIIString(Serializable):
    def __init__(self, length, string):
        self.length = length
        self.string = string

    def __iter__(self):
        return iter([self.x, self.y, self.z])

    @staticmethod
    def from_str(string):
        if string.isascii():
            binary_string = struct.encode("ascii")
            return ASCIIString(len(binary_string), binary_string)
        raise ValueError("A non-ascii string was passed into ascii string. Got: {}".format(string))

    def to_binary(self):
        return [UInt32(self.length), String(self.string)]

