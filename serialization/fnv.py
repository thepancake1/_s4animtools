from _s4animtools.serialization.types.basic import UInt64, UInt32


def get_addon_path():
    """
    I don't think this is used anywhere.
    """
    import os
    return os.path.dirname(os.path.realpath(__file__))


def get_32bit_hash(to_hash, lowercase=True):
    """
    FNV-1 Hash
    I never understood hashing well.

    If the input is a string object, it will optionally lowercase it before
    encoding it in UTF-8.

    In both cases, it will do some black magic to convert a
    string into a 32-bit hash that is totally guaranteed to
    be unique!*

    "Unique" means 1 in 4,294,967,296.
    """

    hval = 0x811c9dc5
    fnvprime = 0x01000193
    fnvsize = 2**32
    if not isinstance(to_hash, bytes):
        if lowercase:
            to_hash = to_hash.lower()
        to_hash = to_hash.encode("UTF-8", "ignore")
    for byte in to_hash:
        hval = (hval * fnvprime) % fnvsize
        hval = hval ^ byte
    return hval

def get_64bithash(to_hash, lowercase=True):
    """
    FNV-1 Hash
    I never understood hashing well.

    If the input is a string object, it will optionally lowercase it before
    encoding it in UTF-8.

    In both cases, it will do some black magic to convert a
    string into a 64-bit hash that is totally guaranteed to
    be unique!*

    "Unique" means 1 in 18,446,744,073,709,551,616.
    """
    hval = 0xcbf29ce484222325
    fnvprime = 0x100000001b3
    fnvsize = 2**64
    if not isinstance(to_hash, bytes):
        if lowercase:
            to_hash = to_hash.lower()
        to_hash = to_hash.encode("UTF-8", "ignore")
    for byte in to_hash:
        hval = (hval * fnvprime) % fnvsize
        hval = hval ^ byte
    return "{}".format(str(hex(hval))[2:].upper()).zfill(8)

def get_64bithash_as_int(to_hash, lowercase=True):
    # TODO why am I doing this
    return int(get_64bithash(to_hash, lowercase), 16)

def hash_name_or_get_hash(string, lowercase=False):
    if string.startswith("0x"):
        return UInt32(int(string.strip(), 16))
    else:
        return UInt32(get_32bit_hash(string.strip(), lowercase=lowercase))

def hash_name_or_get_hash_64(string, lowercase=False):
    if string.startswith("0x"):
        return UInt64(int(string.strip(), 16))
    else:
        return UInt64(get_64bithash_as_int(string.strip(), lowercase=lowercase))