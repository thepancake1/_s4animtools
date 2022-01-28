class Serializable:
    """Serializables can be converted to a list of basic binaries.
    """
    def to_binary(self):
        raise Exception("You must subclass this to use this.")


def get_size(input_element):
    """
    The get_size function goes through an input_element.
    If input_element is a list of bytes, it simply returns
    the size of input_element.

    If input_element is a list or a tuple however, it
    will instead iterate through all children of the
    element and determine the size of those instead.

    It will recursively call get_size until it reaches
    an element that is a bytes element.
    """
    if isinstance(input_element, list) or isinstance(input_element, tuple):
        total_size = 0
        for child_element in input_element:
            total_size += get_size(child_element)
        return total_size
    else:
        if isinstance(input_element, bytes):
            return len(input_element)
        return 0


def recursive_write(input_element, stream):
    """
    The recursive_write function goes through an input_element and
    writes all the values within it to a stream.

    Similarly to the get_size function, if input_element is a bytes object,
    it will write it directly to the stream.

    If it's a list or a tuple, it will instead recursively iterate through all
    the elements within it until it finds a bytes item, which it then writes
    as usual.

    This assumes that the stream has a write function.
    """
    if isinstance(input_element, list) or isinstance(input_element, tuple):
        for child_element in input_element:
            recursive_write(child_element, stream)
    else:
        stream.write(input_element)