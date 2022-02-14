import os
import glob
import shutil
import traceback
from multiprocessing import Pool

from S4ClipThing.structure.channel_type import SubChannelType
from S4ClipThing.structure.header import Header
from S4ClipThing.structure.clip import S4Clip
from S4ClipThing.types.event_list import ClipEvent

threads_to_start = 2
input_folder = r"E:\Clips 1.81"
output_folder = r"E:\Output Animations"
input_folder = r"E:\Dropbox\Sims 4\Projects\Sims 4 Heights\All Animations"
output_folder = r"E:\Dropbox\Sims 4\Projects\Sims 4 Heights\All Sims Animatons"

sim_rig_names = ["x", "y", "z"]
animal_rig_names = ["ad", "al", "ax", "ad", "ac", "cd", "cl", "cx", "cd", "cc"]
human_rig_names = ["a", "c", "p", "t", "e"]

for file in glob.glob(os.path.join(output_folder, "*")):
    os.remove(file)

def determine_if_clip_name_is_for_a_sim(clip_name):
    for animal_rig_name in animal_rig_names:
        if clip_name.startswith(animal_rig_name + "_"):
            return False

    # reenable this when object support is needed
    for human_rig_name in human_rig_names:
        if clip_name.startswith(human_rig_name + "2o_"):# and not clip_name.endswith("_x"):
            return False

    for animal_rig_name in animal_rig_names:
        if clip_name.startswith(animal_rig_name + "2o_"):
            return False

    for animal_rig_name1 in animal_rig_names:
        for animal_rig_name2 in animal_rig_names:
            if clip_name.startswith(animal_rig_name1 + "2" + animal_rig_name2):
                return False


    for human_rig_name in human_rig_names:
        for animal_rig_name in animal_rig_names:
            if clip_name.startswith(human_rig_name + "2" + animal_rig_name) and not clip_name.endswith("_x"):
                return False

    for animal_rig_name in animal_rig_names:
        for human_rig_name in human_rig_names:
            if clip_name.startswith(human_rig_name + "2" + animal_rig_name) and not clip_name.endswith("_y"):
                return False

    if clip_name.startswith("o_"):
        return False

    return True

def read_clip_file(file):
    try:
        with open(file, "rb") as clip_file:
            header, clip_name, events = Header().deserialize(clip_file)
            is_rig_a_sim_rig = determine_if_clip_name_is_for_a_sim(clip_name)
            if is_rig_a_sim_rig:
                shutil.copy(file, os.path.join(output_folder, os.path.basename(file)))
            #clip, channels = S4Clip().deserialize(clip_file, file.split("/")[-1])
            #for channel in channels:
            #    channel.dump(clip_name, output_folder)
            #ClipEvent().dump(clip_name, output_folder, events)
        return os.path.basename(file)

    except Exception as e:
        traceback.print_exc()



if __name__ == "__main__":
    files = []
    idx = 0
    for file in glob.glob(os.path.join(input_folder, "*.Clip")):
        basename = os.path.basename(file)
        if file.endswith(".Clip"):
            name = basename.split("!")[2].split(".")[1]
            files.append(file)
            idx += 1
    with Pool(threads_to_start) as pool:
        vo_clips = pool.map(read_clip_file, files)

