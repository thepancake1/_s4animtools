from struct import pack, unpack

"""
Basic Types are the types that go into a file. 
These include things like an array of bytes, 
an 8, 16, 32, or 64 bit integer, or a string.
"""

class Bytes:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return self.value


class Byte:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return pack("<B", self.value)


class UInt16:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return pack("<H", self.value)


class UInt32:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return pack("<L", self.value)

    @staticmethod
    def deserialize(value):
        return unpack("<L", value)[0]


class UInt64:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return pack("<Q", self.value)

    @staticmethod
    def deserialize(value):
        return unpack("<Q", value)[0]


class Int32:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return pack("<l", self.value)


class Float32:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return pack("<f", self.value)

    @staticmethod
    def deserialize(value):
        return unpack("<f", value)[0]


class String:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return self.value.encode("ascii")

