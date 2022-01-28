import _s4animtools
from _s4animtools.clip_processing.value_types import uint32, float32, serializable_bytes, byte8, uint64



def get_null_terminated_string(string):
    if len(string) >= 128:
        raise OverflowError("One of your sound or effect names is too long. Please rename it. Maximum limit is 128 bytes.")
    for padding in range(128 - len(string)):
        string += bytes([0])
    return string

def get_bytes_from_string(string):
    try:
        ascii_string = string.lstrip().encode("ascii")
    except UnicodeEncodeError:
        raise Exception("Your sound or effect name has non-ascii characters. Please remove this if you want to export.")
    return serializable_bytes(get_null_terminated_string(ascii_string))

def get_hash_from_actor_name_or_hash(string, lowercase=False):
    if string.startswith("0x"):
        return uint32(int(string.strip(), 16))
    else:
        return uint32(_s4animtools.clip_processing.test_tool.get_hash_from_bone_name(string.strip(), lowercase=lowercase))

def get_int_from_hex_string_or_int(string):
    if string.startswith("0x"):
        return uint32(int(string.strip(), 16))
    else:
        return uint32(int(string.strip()))


def get_int64_from_hex_string_or_int(string):
    if string.startswith("0x"):
        return uint64(int(string.strip(), 16))
    else:
        return uint64(int(string.strip()))

class ParentEvent:
    arg_count = 4
    def __init__(self, timecode, child_actor, parent_actor, parent_actor_bone):
        self.event_type = uint32(1)
        self.length = uint32(52)
        self.header1 = uint32(1)
        self.header2 = uint32(0xc6)
        self.timecode = float32(float(timecode))
        self.child_actor = get_hash_from_actor_name_or_hash(child_actor)
        if parent_actor.lstrip() != "0":
            self.parent_actor = get_hash_from_actor_name_or_hash(parent_actor)
        else:
            self.parent_actor = uint32(0)
        if parent_actor_bone.lstrip() != "0":
            self.parent_actor_bone = get_hash_from_actor_name_or_hash(parent_actor_bone, lowercase=True)
        else:
            self.parent_actor_bone = uint32(0)
        self.unused_entry = uint32(0)
    def serialize(self):
        identity_floats = [float32(0), float32(0), float32(1), float32(0), float32(0), float32(0)]

        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.child_actor, self.parent_actor, self.parent_actor_bone, self.unused_entry, *identity_floats]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.serialize())

        return serialized_stuff

class ScriptEvent:
    arg_count = 2

    def __init__(self, timecode, script_event):
        self.event_type = uint32(4)
        self.length = uint32(12)
        self.header1 = uint32(int(script_event))
        self.header2 = uint32(6)
        self.timecode = float32(float(timecode))
    def serialize(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.serialize())

        return serialized_stuff

class SuppressLipsyncEvent:
    arg_count = 2

    def __init__(self, timecode, duration):
        self.event_type = uint32(19)
        self.length = uint32(16)
        self.header1 = uint32(1)
        self.header2 = uint32(100)
        self.timecode = float32(float(timecode))
        self.duration = float32(float(duration))

    def serialize(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode, self.duration]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.serialize())

        return serialized_stuff

class ReactionEvent:
    arg_count = 2
    def __init__(self, timecode, reaction_name):
        self.event_type = uint32(13)
        self.length = uint32(268)
        self.header1 = uint32(1)
        self.header2 = uint32(4)
        self.timecode = float32(float(timecode))
        reaction_name = reaction_name.lstrip().encode("ascii")
        self.reaction_name = reaction_name
        for padding in range(256 - len(reaction_name)):
            self.reaction_name += bytes([0])

        self.reaction_name = serializable_bytes(self.reaction_name)
    def serialize(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.reaction_name]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.serialize())

        return serialized_stuff


class SnapEvent:
    arg_count = 9
    def __init__(self, timecode, actor, t1, t2, t3, q1, q2, q3, q4):
        self.event_type = uint32(12)
        self.length = uint32(44)
        self.header1 = uint32(2)
        self.header2 = uint32(134)
        self.timecode = float32(float(timecode))
        self.actor = get_hash_from_actor_name_or_hash(actor)
        translations = []
        quats = []

        for q in [q1, q2, q3, q4]:
            quats.append(float32(float(q.lstrip())))
        for t in [t1, t2, t3]:
            translations.append(float32(float(t.lstrip())))

        self.offset_q = quats
        self.offset_t = translations
    def serialize(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.actor, *self.offset_q, *self.offset_t]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.serialize())

        return serialized_stuff



class VisibilityEvent:
    arg_count = 3
    def __init__(self, timecode, actor_name, visible):
        self.event_type = uint32(6)
        self.length = uint32(17)
        self.header1 = uint32(1)
        self.header2 = uint32(0x6)
        self.timecode = float32(float(timecode))
        self.actor_name = get_hash_from_actor_name_or_hash(actor_name)
        self.visible = byte8(int(visible))
    def serialize(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.actor_name, self.visible]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.serialize())

        return serialized_stuff


class SoundEvent:
    arg_count = 2
    def __init__(self, timecode, sound_effect_name):
        self.event_type = uint32(3)
        self.length = uint32(140)
        self.header1 = uint32(0)
        self.header2 = uint32(0)
        self.timecode = float32(float(timecode))
        sfx_name = sound_effect_name.lstrip().encode("ascii")
        self.sound_effect_name = serializable_bytes(get_null_terminated_string(sfx_name))
    def serialize(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.sound_effect_name]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.serialize())

        return serialized_stuff


class PlayEffectEvent:
    arg_count = 6
    def __init__(self, timecode, effect_name, actor_name_or_hash, bone_name_hash, u1, u2, slot_name):
        self.event_type = uint32(5)
        self.length = uint32(292)
        self.header1 = uint32(2)
        self.header2 = uint32(0)
        self.timecode = float32(float(timecode))
        self.effect_name = get_bytes_from_string(effect_name)
        self.actor_hash = get_hash_from_actor_name_or_hash(actor_name_or_hash)
        self.bone_name_hash = get_hash_from_actor_name_or_hash(bone_name_hash)
        self.u1 = get_int64_from_hex_string_or_int(u1)
        self.u2 = get_int64_from_hex_string_or_int(u2)
        self.slot_name = get_bytes_from_string(slot_name)
    def serialize(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.effect_name, self.actor_hash, self.bone_name_hash, self.u1, self.u2, self.slot_name]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.serialize())

        return serialized_stuff


class StopEffectEvent:
    arg_count = 4
    def __init__(self, timecode, slot_name, u2, b1):
        self.event_type = uint32(10)
        self.length = uint32(21)
        self.header1 = uint32(2)
        self.header2 = uint32(0)
        self.timecode = float32(float(timecode))
        self.slot_name = get_hash_from_actor_name_or_hash(slot_name)
        self.u2 = get_hash_from_actor_name_or_hash(u2)
        self.b1 = byte8(int(b1))
    def serialize(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                    self.u1, self.u2, self.b1]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.serialize())

        return serialized_stuff

class FocusCompatibilityEvent:
    arg_count = 3
    def __init__(self, timecode, end_timecode, level):
        self.event_type = uint32(18)
        self.length = uint32(17)
        self.header1 = uint32(1)
        self.header2 = uint32(256)
        self.timecode = float32(float(timecode))
        self.end_timecode = float32(float(end_timecode))
        self.level = byte8(int(level))
    def serialize(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.end_timecode, self.level]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.serialize())

        return serialized_stuff