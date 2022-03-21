from _s4animtools.serialization.types.basic import UInt32, Bytes, Float32
class VertexGroup:
    def __init__(self, name, matrix):
        self.name = name
        self.flattened_matrix = matrix
class Skin:
    def __init__(self, identifier = 0):
        self.identifier = identifier
        self.version = 0
        self.count = 0
        self.hashes = []
        self.matrices = []

    def read(self, stream):
        self.identifier = stream.read(4)
        self.version = UInt32.deserialize(stream.read(4))
        self.count = UInt32.deserialize(stream.read(4))
        self.hashes = []
        self.matrices = []
        for i in range(self.count):
            self.hashes.append(UInt32.deserialize(stream.read(4)))
        for i in range(self.count):
            matrix = []
            for v in range(12):
                matrix.append(Float32.deserialize(stream.read(4)))
            self.matrices.append(matrix)
        return self

    def serialize(self):
        serialized_stuff = []
        hashes = []
        count = 0
        for hash in self.hashes:
            hashes.append(UInt32(hash))
            count += 1
        count = UInt32(count)

        matrix_values = []
        for matrix in self.matrices:
            for value in matrix:
                matrix_values.append(Float32(value))

        data = [Bytes(self.identifier), UInt32(self.version), count, *hashes, *matrix_values]


        for value in data:
            serialized_stuff.append(value.serialize())

        return serialized_stuff

    @property
    def value(self):
        return self.serialize()
    def __repr__(self):
        return "{}".format(vars(self))

if __name__ == "__main__":
    pass