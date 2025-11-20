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
        else:
            raise TypeError("get size expects all elements to be lists,tuples or bytes, got: {}".format(type(input_element)))

def get_binary_size(element):
    """
    Calls to_binary on the element and returns the size of the binary data.
    """
    if hasattr(element, 'to_binary'):
        binary_data = element.to_binary()
        return len(binary_data)
    else:
        raise TypeError("Element does not have a to_binary method.")

def concatenate_bytes(recursive_list_of_either_bytes_or_list):
    """
    The concatenate_bytes function takes a list of bytes or lists of bytes or bytearrays
    and concatenates them into a single bytes object.
    """
    # This was supposed to be better than recursive_write, but it ends up looking terrible.
    # Just don't think about it too much.
    if isinstance(recursive_list_of_either_bytes_or_list, list) or isinstance(recursive_list_of_either_bytes_or_list, tuple):
        concatenated = bytearray()
        for item in recursive_list_of_either_bytes_or_list:
            if isinstance(item, bytes) or isinstance(item, bytearray):
                concatenated.extend(item)
            elif isinstance(item, list) or isinstance(item, tuple):
                concatenated.extend(concatenate_bytes(item))
            else:
                raise TypeError("Expected bytes, bytearray, list or tuple, got: {}".format(type(item)))
        return bytes(concatenated)
    else:
        raise TypeError("Expected a list or tuple of bytes or lists of bytes, got: {}".format(type(recursive_list_of_either_bytes_or_list)))

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
   # print(input_element)
    #print(type(input_element))
    if isinstance(input_element, list) or isinstance(input_element, tuple):
        for child_element in input_element:
            recursive_write(child_element, stream)
    else:
        stream.write(input_element)