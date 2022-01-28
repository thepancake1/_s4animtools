from struct import pack, unpack

class serializable_bytes:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return self.value
class byte8:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return pack("<B", self.value)
class uint16:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return pack("<H", self.value)


class uint32:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return pack("<L", self.value)

    @staticmethod
    def deserialize(value):
        return unpack("<L", value)[0]

class uint64:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return pack("<Q", self.value)

    @staticmethod
    def deserialize(value):
        return unpack("<Q", value)[0]


class int32:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return pack("<l", self.value)



class float32:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return pack("<f", self.value)

    @staticmethod
    def deserialize(value):
        return unpack("<f", value)[0]

class serializable_string:
    def __init__(self, value):
        self.value = value

    def serialize(self):
        return self.value.encode("ascii")

