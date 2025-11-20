from s4animtools.serialization.types.basic import u32, Bytes, f32
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

    def from_binary(self, stream):
        self.identifier = stream.read(4)
        self.version = u32.from_binary(stream.read(4))
        self.count = u32.from_binary(stream.read(4))
        self.hashes = []
        self.matrices = []
        for i in range(self.count):
            self.hashes.append(u32.from_binary(stream.read(4)))
        for i in range(self.count):
            matrix = []
            for v in range(12):
                matrix.append(f32.from_binary(stream.read(4)))
            self.matrices.append(matrix)
        return self

    def to_binary(self):
        serialized_stuff = []
        hashes = []
        count = 0
        for hash in self.hashes:
            hashes.append(u32(hash))
            count += 1
        count = u32(count)

        matrix_values = []
        for matrix in self.matrices:
            for value in matrix:
                matrix_values.append(f32(value))

        data = [Bytes(self.identifier), u32(self.version), count, *hashes, *matrix_values]


        for value in data:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff

    @property
    def value(self):
        return self.to_binary()
    def __repr__(self):
        return "{}".format(vars(self))

if __name__ == "__main__":
    pass