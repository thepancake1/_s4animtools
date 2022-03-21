from _s4animtools.serialization.types.basic import UInt32
from _s4animtools.serialization.types.basic import UInt64


class TGI:
    def __init__(self):
        self.i = 0
        self.t = 0
        self.g = 0

    def read(self, stream):
        self.i = stream.u64()
        self.t = stream.u32()
        self.g = stream.u32()
        return self

    def serialize(self):
        data = [UInt64(self.i), UInt32(self.t), UInt32(self.g)]
        serialized_stuff = []
        for value in data:
            serialized_stuff.append(value.serialize())

        return serialized_stuff

    def __repr__(self):
        return "{}".format(vars(self))