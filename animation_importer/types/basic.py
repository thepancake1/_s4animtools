import traceback
from struct import pack, unpack

class uint16(int):

    def serialize(self):
        pass

    @staticmethod
    def deserialize(data):
        return unpack("<H", data.read(2))[0]

    @staticmethod
    def space():
        return 2

class uint32(int):

    def serialize(self):
        pass

    @staticmethod
    def deserialize(data):
        try:
            return unpack("<L", data.read(4))[0]
        except:
            print(data.tell())
            traceback.print_exc()
    @staticmethod
    def space():
        return 4

class float32(float):

    def serialize(self):
        pass

    @staticmethod
    def deserialize(data):
        #print(data)
        return unpack("<f", data.read(4))[0]

    @staticmethod
    def space():
        return 4

class string(str):

    def serialize(self):
        pass

    @staticmethod
    def deserialize(data):
        length = uint32().deserialize(data)
        return length, data.read(length).decode()

    @staticmethod
    def space():
        return 0

class byte(bytes):

    def serialize(self):
        pass

    @staticmethod
    def deserialize(data, size):
        return data.read(size)


    @staticmethod
    def space():
        return 0


class intByte:

    def serialize(self):
        pass

    @staticmethod
    def deserialize(data):
        return int.from_bytes(data.read(1), "little")
