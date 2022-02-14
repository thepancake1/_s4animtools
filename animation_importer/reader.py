import os
import glob
import traceback
from collections import defaultdict

from bpy
from _s4animtools.animation_importer.structure.header import Header
from _s4animtools.animation_importer.structure.clip import S4Clip
from _s4animtools.animation_importer.types.event_list import ClipEvent


def read_clip_file(file):
    try:
        with open(file, "rb") as clip_file:
            header, clip_name, events = Header().deserialize(clip_file)
            clip, channels = S4Clip().deserialize(clip_file, file.split("/")[-1])
            alL_channel_data_string = defaultdict(str)
            for channel in channels:
                bone_data = channel.dump(clip_name)
                for channel_data in bone_data.keys():
                    alL_channel_data_string[channel_data] = bone_data[channel_data]
            events_string = ClipEvent().dump(events)
        return os.path.basename(file)

    except Exception as e:
        traceback.print_exc()



if __name__ == "__main__":
    files = []
    idx = 0
    for file in glob.glob(os.path.join(bpy.context.object.clip_input_directory, "*.Clip")):
        basename = os.path.basename(file)
        if file.endswith(".Clip"):
            name = basename.split("!")[2].split(".")[1]
            files.append(file)
            idx += 1
            read_clip_file(files[idx])

