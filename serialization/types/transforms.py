from s4animtools.serialization.types.basic import Float32
from s4animtools.serialization import Serializable

"""
Transform Types are types used for representing exported data 
that build on top on the Basic types but are used for things 
like a Vector3 or a Quaternion.
"""


class Vector3(Serializable):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __iter__(self):
        return iter([self.x, self.y, self.z])

    @staticmethod
    def from_str(string, separator=","):
        values = string.split(separator)
        if len(values) != 3:
            raise ValueError("Vector3 requires 3 values, Got: {}".format(values))
        return Vector3(*map(float, values))

    def to_binary(self):
        return list(map(Float32, self))


class Quaternion4(Serializable):
    def __init__(self, w, x, y, z):
        self.w = w
        self.x = x
        self.y = y
        self.z = z

    def __iter__(self):
        return iter([self.w, self.x, self.y, self.z])

    @staticmethod
    def from_str(string, separator=","):
        values = string.split(separator)
        if len(values) != 4:
            raise ValueError("Quaternion requires 4 values, Got: {}".format(values))
        return Quaternion4(*map(float, values))

    def to_binary(self):
        return list(map(Float32, self))

