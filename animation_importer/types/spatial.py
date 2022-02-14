from _s4animtools.animation_importer.types.basic import float32

class Quaternion(list):
    @staticmethod
    def deserialize(data):
        new_quaternion = []
        for i in range(4):
            new_quaternion.append(float32().deserialize(data))
        return Quaternion(new_quaternion)

    @staticmethod
    def space():
        return 4 * 4

class Vector3(list):
    @staticmethod
    def deserialize(data):
        new_vector3 = []
        for i in range(3):
            new_vector3.append(float32().deserialize(data))
        return Vector3(new_vector3)

    @staticmethod
    def space():
        return 4 * 3