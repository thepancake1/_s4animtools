from _s4animtools.clip_processing.value_types import uint32, uint64, uint16, serializable_string, serializable_bytes, float32


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
        self.version = uint32.deserialize(stream.read(4))
        self.count = uint32.deserialize(stream.read(4))
        self.hashes = []
        self.matrices = []
        for i in range(self.count):
            self.hashes.append(uint32.deserialize(stream.read(4)))
        for i in range(self.count):
            matrix = []
            for v in range(12):
                matrix.append(float32.deserialize(stream.read(4)))
            self.matrices.append(matrix)
        return self

    def serialize(self):
        serialized_stuff = []
        hashes = []
        count = 0
        for hash in self.hashes:
            hashes.append(uint32(hash))
            count += 1
        count = uint32(count)

        matrix_values = []
        for matrix in self.matrices:
            for value in matrix:
                matrix_values.append(float32(value))

        data = [serializable_bytes(self.identifier), uint32(self.version), count, *hashes, *matrix_values]


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