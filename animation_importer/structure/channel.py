import os

from S4ClipThing.types.basic import uint32, float32, uint16, byte, intByte
from S4ClipThing.structure.channel_type import ChannelType, SubChannelType
from S4ClipThing.structure.channel_width import GetWidthForChannelType
from S4ClipThing.structure.frames import Frame
class Channel:
    def __str__(self):
        return "{}".format(vars(self))

    def __repr__(self):
        return "{}".format(vars(self))

    def convert_into_value(self, value):
        return value

    def deserialize(self, data, channelDataOffset):
        self.dataOffset = uint32.deserialize(data)
        self.target = uint32.deserialize(data)
        self.offset = float32.deserialize(data)
        self.scale = float32.deserialize(data)
        self.num_frames = uint16.deserialize(data)
        self.channelType = ChannelType(intByte.deserialize(data))
        self.channelSubTarget = SubChannelType(intByte.deserialize(data))

        self.frames = []
        currentPos = data.tell()
        # Channel data offset has -48 offset.
        data.seek(self.dataOffset + channelDataOffset - 48, 0)

        for i in range(self.num_frames):
            last_frame_tick = self.frames[-1].startTick if len(self.frames) > 0 else -1
            self.frames.append(Frame().deserialize(data, self.channelType, self.offset, self.scale, last_frame_tick))
        data.seek(currentPos, 0)
        return self
    def bone_name(self):
        with open("bone hashes.txt", "r") as bone_hashes:
            lines = bone_hashes.readlines()
            for line in lines:
                try:
                    bone_name, bone_id = line.split(" ")
                    if int(bone_id, 16) == self.target:
                        return bone_name
                except ValueError:
                    pass
        return hex(self.target)[2:]
    @staticmethod
    def add(value):
        a, b = value
        return a + b

    def dump(self,animation_name, base_path):
        if ":" in animation_name:
            animation_name = animation_name.replace(":", "_", 1)

        if not os.path.exists(base_path):
            os.mkdir(base_path)
        if not os.path.exists(os.path.join(base_path, animation_name)):
            os.mkdir(os.path.join(base_path, animation_name))
        if len(self.frames) > 0:
          with open(os.path.join(base_path, animation_name, self.bone_name() + "-" + str(self.channelType) + "-" + str(self.channelSubTarget) +".channel"), "w") as file:
                #print(self.scale, self.offset)
                min, max = 9999, -9999
                for frame in self.frames:
                    frame_indices = frame.values

                    frame_indices = list(map(self.convert_into_value, frame_indices))
                   # print(frame_indices)

                    for frame_val in frame_indices:
                        if max < frame_val:
                            max = frame_val
                        if min > frame_val:
                            min = frame_val

                    frame_indices = list(map(str, frame_indices))

                    file.write("{},{}\n".format(frame.startTick, ",".join(frame_indices)))
                   # file.write("{}\n".format(frame.flags))
                #print(min, max)
                offset = (min + max) / 2
                scale = (min - max) / 2
                file.write("{},{}\n".format(offset, scale))
                file.write("True {},{}".format(self.offset, self.scale))

