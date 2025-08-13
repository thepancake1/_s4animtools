from s4animtools.game_types import uint8, uint16, uint32, uint64, float32, int32


class StreamReader:
    def __init__(self, file):
        self.filename = file
        self.stream = open(file, "rb").read()
        self.current_pos = 0
    def u8(self, raw=False):
        self.current_pos += 1
        return uint8().read(self.stream[self.current_pos-1:self.current_pos])

    def u16(self, raw=False):
        self.current_pos += 2
        return uint16().read(self.stream[self.current_pos-2:self.current_pos])

    def u32(self, raw=False):
        self.current_pos += 4

        value = self.stream[self.current_pos-4:self.current_pos]

        if not raw:
            return uint32().read(value)
        else:
            return value

    def s32(self, raw=False):
        self.current_pos += 4

        value = self.stream[self.current_pos-4:self.current_pos]

        if not raw:
            return int32().read(value)
        else:
            return value


    def u64(self, raw=False):
        self.current_pos += 8

        return uint64().read(self.stream[self.current_pos-8:self.current_pos])

    def float32(self, raw=False):
        self.current_pos += 4
        return float32().read(self.stream[self.current_pos-4:self.current_pos])
    def tell(self):
        return self.current_pos

    def seek(self, value):
        old_pos = self.current_pos
        self.current_pos = value
        return old_pos
    def read_string(self, length):
        self.current_pos += length
        try:
            return self.stream[self.current_pos-length:self.current_pos].decode("utf-8")
        except UnicodeDecodeError:
            return "Unreadable Name"
    def read(self, byte_count):
        self.current_pos += byte_count
        return self.stream[self.current_pos - byte_count: self.current_pos]