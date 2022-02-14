import enum
import os
import struct

from S4ClipThing.types.basic import uint16, uint32, string, byte

class SizeString:
    def __init__(self):
        self.string = ""

    def deserialize(self, data):
        size = int.from_bytes(data[0:4], "little")
        self.string = data[4:4+size]
        return self.string.decode("ascii"), 4+size

class EventTypes(enum.IntEnum):
    PARENT = 1
    SFX = 3
    SCRIPT = 4
    EFFECT = 5
    VISIBILITY = 6
    STOP_EFFECT = 10
    LIPSYNC = 19

class ClipEvent(list):
    @staticmethod
    def deserialize(clip_name, data, repeat, version):
        clip_events = []
        vo_clips = []
        effect_events = []
        parent_events = []
        lipsync_events = []
        stop_effect_events = []
        visiblity_events = []
        script_events = []
        if version < 14 or version > 16:
            raise Exception("This doesn't support this clip version.")
        for i in range(repeat):
            clip_event_type = uint32().deserialize(data)
            data_size = uint32().deserialize(data)
            arg1 = byte().deserialize(data, data_size)

            if clip_event_type == EventTypes.PARENT:
                header1 = arg1[0:4]
                header2 = arg1[4:8]
                timestamp = round(struct.unpack("f", arg1[8:12])[0], 3)
                to_parent_actor = int.from_bytes(arg1[12:16], "little")
                parent_actor = int.from_bytes(arg1[16:20], "little")
                parent_bone = int.from_bytes(arg1[20:24], "little")

                parent_events.append([str(timestamp), hex(to_parent_actor), hex(parent_actor), hex(parent_bone)])

            elif clip_event_type == EventTypes.SFX:
                header1 = arg1[0:4]
                header2 = arg1[4:8]
                timestamp = round(struct.unpack("f", arg1[8:12])[0], 3)
                if version == 16:
                    vo_clip, _ = SizeString().deserialize(arg1[12:])
                elif version == 14:
                    vo_clip = arg1[12:].decode("ascii").split('\x00')[0]
                vo_clips.append((str(timestamp), vo_clip))

            elif clip_event_type == EventTypes.SCRIPT:
                header1 = int.from_bytes(arg1[0:4], "little")
                xevt = int.from_bytes(arg1[4:8], "little")
                timestamp = round(struct.unpack("f", arg1[8:12])[0], 3)
                script_events.append([str(timestamp), str(xevt)])

            elif clip_event_type == EventTypes.EFFECT:
                if version == 16:
                    header1 = arg1[0:4]
                    header2 = arg1[4:8]
                    timestamp = round(struct.unpack("f", arg1[8:12])[0], 3)
                    effect_name, size = SizeString().deserialize(arg1[12:])
                    actor_hash = int.from_bytes(arg1[12+size:12+size+4], "little")
                    bone_name_hash = int.from_bytes(arg1[12+size+4:12+size+8], "little")
                    u1 = int.from_bytes(arg1[12+size+8:12+size+16], "little")
                    u2 = int.from_bytes(arg1[12+size+16:12+size+24], "little")
                    slot_string, size2 = SizeString().deserialize(arg1[36+size:])
                elif version == 14:
                    header1 = arg1[0:4]
                    header2 = arg1[4:8]
                    timestamp = round(struct.unpack("f", arg1[8:12])[0], 3)
                    effect_name = arg1[12:12+128].decode("ascii").split('\x00')[0]
                    actor_hash = int.from_bytes(arg1[140:140+4], "little")
                    bone_name_hash = int.from_bytes(arg1[144:144+4], "little")
                    u1 = int.from_bytes(arg1[148:148+8], "little")
                    u2 = int.from_bytes(arg1[156:156+8], "little")
                    slot_string = arg1[164:164+128].decode("ascii").split('\x00')[0]

                effect_events.append([str(timestamp), effect_name, hex(actor_hash), hex(bone_name_hash), str(u1), str(u2), slot_string])

            elif clip_event_type == EventTypes.VISIBILITY:
                header1 = arg1[0:4]
                header2 = arg1[4:8]
                timestamp = round(struct.unpack("f", arg1[8:12])[0], 3)
                actor_name = int.from_bytes(arg1[12:16], "little")
                visible = int.from_bytes(arg1[16:17], "little")

                visiblity_events.append([str(timestamp), hex(actor_name), str(visible)])

            elif clip_event_type == EventTypes.STOP_EFFECT:
                #print(clip_name)
                header1 = arg1[0:4]
                header2 = arg1[4:8]
                timestamp = round(struct.unpack("f", arg1[8:12])[0], 3)
                unique_vfx_id = int.from_bytes(arg1[12:16], "little")
                u2 = int.from_bytes(arg1[16:20], "little")
                if u2 != 0:
                    print(clip_name, u1, hex(u2))
                b1 = int.from_bytes(arg1[20:21], "little")
                stop_effect_events.append([str(timestamp), hex(unique_vfx_id), hex(u2), str(b1)])
            elif clip_event_type == 12:
                header1 =  int.from_bytes(arg1[0:4], "little")
                header2 =  int.from_bytes(arg1[4:8], "little")

            elif clip_event_type == 18:
                header1 =  int.from_bytes(arg1[0:4], "little")
                header2 =  int.from_bytes(arg1[4:8], "little")
                timestamp = round(struct.unpack("f", arg1[8:12])[0], 3)
                timestamp2 = round(struct.unpack("f", arg1[12:16])[0], 3)

                level = int.from_bytes(arg1[16:], "little")

            elif clip_event_type == EventTypes.LIPSYNC:
                header1 = arg1[0:4]
                header2 = arg1[4:8]
                timestamp = round(struct.unpack("f", arg1[8:12])[0], 3)
                duration = round(struct.unpack("f", arg1[12:16])[0], 3)

                lipsync_events.append([str(timestamp), str(duration)])





            clip_event = ClipEvent([clip_event_type, data_size, arg1])
            clip_events.append(clip_event)
        return clip_events, [vo_clips, effect_events, parent_events, lipsync_events, stop_effect_events, visiblity_events, script_events]

    def dump(self, animation_name, base_path, events):
        names = ["SOUNDS", "VFX", "PARENT", "SUPPRESS LIPSYNC", "STOP EFFECT", "VISIBILITY", "SCRIPT"]
        if ":" in animation_name:
            animation_name = animation_name.replace(":", "_", 1)
        if not os.path.exists(base_path):
            os.mkdir(base_path)
        if not os.path.exists(os.path.join(base_path, animation_name)):
            os.mkdir(os.path.join(base_path, animation_name))
        with open(
            os.path.join(base_path, animation_name, "animation_events.txt"), "w") as file:
            for idx, item in enumerate(events):
                name = names[idx]
                file.write(f"==={name}===\n")
                for event in item:
                    file.write(",".join(event)+"\n")

        # print(self.scale, self.offset)

    @staticmethod
    def space():
        return 0
