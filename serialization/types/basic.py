from struct import pack, unpack

"""
Basic Types are the types that go into a file. 
These include things like an array of bytes, 
an 8, 16, 32, or 64 bit integer, or a string.
"""
class Serializable:
    def to_binary(self):
        raise NotImplementedError

    @staticmethod
    def from_binary(reader):
        raise NotImplementedError


class Bytes(Serializable):
    def __init__(self, data:bytes) -> None:
        if not isinstance(data, bytes):
            raise Exception("Bytes data is not bytes")
        self.data = data

    def to_binary(self) -> bytes:
        return self.data

    def from_binary(reader) -> None:
        raise Exception("Bytes.from_binary is not implemented. Use a subclass that has length control instead")

class u8:
    def __init__(self, data:int) -> None:
        self.data = data

    def to_binary(self) -> bytes:
        return pack("<B", self.data)

    @staticmethod
    def from_binary(reader) -> int:
        data = reader.read(1)
        return unpack("<B", data)[0]
class u16:
    def __init__(self, data) -> None:
        self.data = data

    def to_binary(self) -> bytes:
        return pack("<H", self.data)

    @staticmethod
    def from_binary(reader) -> int:
        data = reader.read(2)
        return unpack("<H", data)[0]
class u32:
    def __init__(self, data):
        self.data = data

    def to_binary(self) -> bytes:
        return pack("<L", self.data)

    @staticmethod
    def from_binary(reader) -> int:
        data = reader.read(4)
        return unpack("<L", data)[0]

class u64:
    def __init__(self, data):
        self.data = data

    def to_binary(self) -> bytes:
        return pack("<Q", self.data)

    @staticmethod
    def from_binary(reader) -> int:
        data = reader.read(8)
        return unpack("<Q", data)[0]


class i32:
    def __init__(self, data):
        self.data = data

    def to_binary(self) -> bytes:
        return pack("<l", self.data)

    @staticmethod
    def from_binary(reader) -> int:
        data = reader.read(4)
        return unpack("<l", data)[0]

class f32:
    def __init__(self, data):
        self.data = data

    def to_binary(self) -> bytes:
        return pack("<f", self.data)

    @staticmethod
    def from_binary(reader) -> int:
        data = reader.read(4)
        return unpack("<f", data)[0]



class String:
    def __init__(self, data):
        self.data = data

    def to_binary(self) -> bytes:
        return self.data.encode("ascii")

    @staticmethod
    def from_binary(reader) -> str:
        raise Exception("String.from_binary is not implemented. Use a subclass that has length control instead")
