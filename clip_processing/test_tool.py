import sys
import inspect


def getAddonPath():
    import os
    return os.path.dirname(os.path.realpath(__file__))

def get_hash_from_bone_name(bone_name, lowercase=True):
    hval = 0x811c9dc5
    fnvprime = 0x01000193
    fnvsize = 2**32
    if not isinstance(bone_name, bytes):
        if lowercase:
            bone_name = bone_name.lower()
        bone_name = bone_name.encode("UTF-8", "ignore")
    for byte in bone_name:
        hval = (hval * fnvprime) % fnvsize
        hval = hval ^ byte
    return hval

def get_64bithash(name):
    hval = 0xcbf29ce484222325
    fnvprime = 0x100000001b3
    fnvsize = 2**64
    if not isinstance(name, bytes):
        name = name.lower().encode("UTF-8", "ignore")
    for byte in name:
        hval = (hval * fnvprime) % fnvsize
        hval = hval ^ byte
    return "{}".format(str(hex(hval))[2:].upper()).zfill(8)

def recursive_write(input_element, stream):
    #print(input_element)
    if isinstance(input_element, list) or isinstance(input_element, tuple):
        for child_element in input_element:
            recursive_write(child_element, stream)
    else:
        stream.write(input_element)

def get_size(input_element):
    if isinstance(input_element, list) or isinstance(input_element, tuple):
        total_size = 0
        for child_element in input_element:
            total_size += get_size(child_element)
        return total_size
    else:
        if isinstance(input_element, bytes):
            return len(input_element)
        return 0
if __name__ == "__main__":
    print(get_hash_from_bone_name("b__ROOT__"))
