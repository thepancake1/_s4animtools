from s4animtools.serialization.types.basic import u32, Serializable
from s4animtools.serialization.types.basic import u64


class TGI(Serializable):
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
        data = [u64(self.i), u32(self.t), u32(self.g)]
        serialized_stuff = []
        for value in data:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff

    def __repr__(self):
        return "{}".format(vars(self))