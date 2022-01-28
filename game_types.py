import enum
import struct
"""
This sucks.
"""

class DataTypes(enum.IntEnum):
    uint8 = 0
    uint16 = 1
    uint32 = 2
    uint64 = 3
    float32 = 4


class ReadableData:
    def __init__(self, raw_data=None, hex=False):
        self.hex = hex
        self.data = 0
        if raw_data is not None:
            self.read(raw_data)

    def read(self, raw_data):
        try:
            raw_data = raw_data()
           # print("Raw data is a function")
        except:
           # print("Raw data is not a function")
            pass
        return raw_data

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if self.hex:
            return "{}".format(hex(self.data))
        return "{}".format(self.data)


    def __index__(self):
        return self.data

    def __gt__(self, b):
        try:
            return self.data > b
        except:
            return self.data > b.data


    def __ge__(self, b):
        try:
            return self.data >= b
        except:
            return self.data >= b.data
    def __lt__(self, b):
        try:
            return self.data < b
        except:
            return self.data < b.data

    def __lshift__(self, b):
        return self.data << b

    def __rshift__(self, b):
        return self.data >> b

    def __xor__(self, b):
        return self.data ^ b
    def __and__(self, b):
        return self.data & b

    def __eq__(self, b):
        if self.data < b + 0.0001:
            if self.data > b - 0.0001:
                return True
        return False


    def __truediv__(self, b):
        try:
            return self.data / b
        except:
            return self.data / b.data


    def __add__(self, b):
        a = self
        try:
            a = a.data
        except:
            pass
        return a + b


    def __sub__(self, b):
        try:
            return self.data - b
        except:
            return self.data - b.data

    def __radd__(self, b):
        a = self
        try:
            a = a.data
        except:
            pass
        return a + b
    def __mul__(self, b):
        return self.data * b

    def __int__(self):
        return self.data

    def __hash__(self):
        return hash(self.data)
class uint8(ReadableData):


    def read(self, raw_data):
        raw_data = super().read(raw_data)
        self.data = int.from_bytes(raw_data, "little")

        return self.data

    def size(self):
        return 8

class int8(ReadableData):


    def read(self, raw_data):
        raw_data = super().read(raw_data)
        self.data = int.from_bytes(raw_data, "little",signed=True)

        return self.data

    def size(self):
        return 8


class uint32(uint8):
    def size(self):
        return 32

class int32(int8):
    def size(self):
        return 32


class uint64(uint8):
    def size(self):
        return 64


class int64(int8):
    def size(self):
        return 64

class uint16(uint8):
    def size(self):
        return 16


class int16(int8):
    def size(self):
        return 16


class float32(ReadableData):
    def __mul__(self, b):
        return self.data * b
    def __rmul__(self, b):
        return self.data * b

    def __round__(self, value):
        return round(self.data, value)
    def read(self, raw_data):
        raw_data = super().read(raw_data)
     #   print(raw_data)
        self.data = struct.unpack('f', raw_data)[0]
        return self.data

    def __float__(self):
        return self.data



def read_multiple_of_type(type, repetitions, read_func):
    values = []
    for i in range(repetitions):
        values.append(type(read_func))
    return values