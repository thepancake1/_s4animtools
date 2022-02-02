FLOAT_PRECISION = 7


class F1Palette:
    """
    F1 palettes are used to store data that needs to have full precision. Unlike the Translation channel, which uses 10 bits per
    axis, and unlike the Rotation channel, which uses 12 bits per axis, F1 Palettes use 32 bits per axis.
    """
    def __init__(self):
        self.palette_values = []
        self.palette_values_string = []

    @property
    def palette_size(self):
        return len(self.palette_values)

    def get_palette(self, index):
        """
        Returns a palette from the F1 palette.
        :param index: The index of the palette to return.
        :return: A palette from the F1 palette.
        """
        return self.data[index * 4:index * 4 + 4]

    def get_palette_index(self, palette_value):
        """
        Returns the index of a palette in the F1 palette.
        :param palette_value: The palette value to find the index of.
        """
        for palette_value in self.palette_values:
            if palette_value == palette_value:
                return self.palette_values.index(palette_value)
        return -1

    def try_add_palette_to_palette_values(self, potential_palette_value):
        """
        This checks if a potential palette value already exists in the list, if it already exists, it will be skipped.
        Otherwise, it will be added to the list.
        :param potential_palette_value: The potential palette value to add to the list.
        """
        found_similar = False
        string_representation = str(round(potential_palette_value, FLOAT_PRECISION)).strip()
        if float(string_representation) == 0:
            string_representation = "0"
        if string_representation in self.palette_values_string:
            found_similar = True
            print("Found similar palette value: ",  string_representation, round(potential_palette_value, FLOAT_PRECISION))
        if not found_similar:
            self.palette_values.append(round(potential_palette_value, FLOAT_PRECISION))
            self.palette_values_string.append(string_representation)
        return self.palette_values_string.index(string_representation)