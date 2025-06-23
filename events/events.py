from s4animtools.serialization.types.basic import u32, f32, Bytes, u8, u64

from s4animtools.serialization.fnv import hash_name_or_get_hash


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
    return Bytes(get_null_terminated_string(ascii_string))


def get_int_from_hex_string_or_int(string):
    if string.startswith("0x"):
        return u32(int(string.strip(), 16))
    else:
        return u32(int(string.strip()))


def get_int64_from_hex_string_or_int(string):
    if string.startswith("0x"):
        return u64(int(string.strip(), 16))
    else:
        return u64(int(string.strip()))


class ParentEvent:
    arg_count = 4

    def __init__(self, timecode, child_actor, parent_actor, parent_actor_bone):
        self.event_type = u32(1)
        self.length = u32(52)
        self.header1 = u32(1)
        self.header2 = u32(0xc6)
        self.timecode = f32(float(timecode))
        self.child_actor = hash_name_or_get_hash(child_actor)
        if parent_actor.lstrip() != "0":
            self.parent_actor = hash_name_or_get_hash(parent_actor)
        else:
            self.parent_actor = u32(0)
        if parent_actor_bone.lstrip() != "0":
            self.parent_actor_bone = hash_name_or_get_hash(parent_actor_bone, lowercase=True)
        else:
            self.parent_actor_bone = u32(0)
        self.unused_entry = u32(0)

    def to_binary(self):
        identity_floats = [f32(0), f32(0), f32(1), f32(0), f32(0), f32(0)]

        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.child_actor, self.parent_actor, self.parent_actor_bone, self.unused_entry, *identity_floats]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff


class ScriptEvent:
    arg_count = 2

    def __init__(self, timecode, script_event):
        self.event_type = u32(4)
        self.length = u32(12)
        self.header1 = u32(int(script_event))
        self.header2 = u32(6)
        self.timecode = f32(float(timecode))

    def to_binary(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff


class SuppressLipsyncEvent:
    arg_count = 2

    def __init__(self, timecode, duration):
        self.event_type = u32(19)
        self.length = u32(16)
        self.header1 = u32(1)
        self.header2 = u32(100)
        self.timecode = f32(float(timecode))
        self.duration = f32(float(duration))

    def to_binary(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode, self.duration]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff


class ReactionEvent:
    arg_count = 3

    def __init__(self, timecode, reaction_asm, reaction_state):
        self.event_type = u32(13)
        self.length = u32(268)
        self.header1 = u32(1)
        self.header2 = u32(4)
        self.timecode = f32(float(timecode))
        reaction_asm = reaction_asm.lstrip().encode("ascii")
        self.reaction_asm = reaction_asm
        for padding in range(128 - len(reaction_asm)):
            self.reaction_asm += bytes([0])

        self.reaction_asm = Bytes(self.reaction_asm)
        reaction_state = reaction_state.lstrip().encode("ascii")

        self.reaction_state = reaction_state
        for padding in range(128 - len(reaction_state)):
            self.reaction_state += bytes([0])

        self.reaction_state = Bytes(self.reaction_state)
    def to_binary(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.reaction_asm, self.reaction_state]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff


class SnapEvent:
    arg_count = 9

    def __init__(self, timecode, actor, t1, t2, t3, q1, q2, q3, q4):
        self.event_type = u32(12)
        self.length = u32(44)
        self.header1 = u32(2)
        self.header2 = u32(134)
        self.timecode = f32(float(timecode))
        self.actor = hash_name_or_get_hash(actor)
        translations = []
        quats = []

        for q in [q1, q2, q3, q4]:
            quats.append(f32(float(q.lstrip())))
        for t in [t1, t2, t3]:
            translations.append(f32(float(t.lstrip())))

        self.offset_q = quats
        self.offset_t = translations
        print(quats, translations, actor, timecode)

    def to_binary(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.actor, *self.offset_q, *self.offset_t]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff



class VisibilityEvent:
    arg_count = 3

    def __init__(self, timecode, actor_name, visible):
        self.event_type = u32(6)
        self.length = u32(17)
        self.header1 = u32(1)
        self.header2 = u32(0x6)
        self.timecode = f32(float(timecode))
        self.actor_name = hash_name_or_get_hash(actor_name)
        self.visible = u8(int(visible))

    def to_binary(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.actor_name, self.visible]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff


class SoundEvent:
    arg_count = 2

    def __init__(self, timecode, sound_effect_name):
        self.event_type = u32(3)
        self.length = u32(140)
        self.header1 = u32(0)
        self.header2 = u32(0)
        self.timecode = f32(float(timecode))
        sfx_name = sound_effect_name.lstrip().encode("ascii")
        self.sound_effect_name = Bytes(get_null_terminated_string(sfx_name))

    def to_binary(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.sound_effect_name]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff


class PlayEffectEvent:
    arg_count = 7

    def __init__(self, timecode, effect_name, actor_name_or_hash, bone_name_hash, u1, actor_name_or_hash_2, bone_name_hash_2, slot_name):
        self.event_type = u32(5)
        self.length = u32(292)
        self.header1 = u32(2)
        self.header2 = u32(0)
        self.timecode = f32(float(timecode))
        self.effect_name = get_bytes_from_string(effect_name)
        self.actor_hash = hash_name_or_get_hash(actor_name_or_hash)
        self.bone_name_hash = hash_name_or_get_hash(bone_name_hash, lowercase=True)
        self.u1 = get_int64_from_hex_string_or_int(u1)
        if actor_name_or_hash_2.lstrip() == "0":
            self.actor_hash_2 = u32(0)
        else:
            self.actor_hash_2 = hash_name_or_get_hash(actor_name_or_hash_2)
        if bone_name_hash_2.lstrip() == "0":
            self.bone_name_hash_2 = u32(0)
        else:
            self.bone_name_hash_2 = hash_name_or_get_hash(bone_name_hash_2, lowercase=True)
        self.slot_name = get_bytes_from_string(slot_name)

    def to_binary(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.effect_name, self.actor_hash, self.bone_name_hash, self.u1, self.actor_hash_2, self.bone_name_hash_2, self.slot_name]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff


class StopEffectEvent:
    arg_count = 4

    def __init__(self, timecode, slot_name, u2, b1):
        self.event_type = u32(10)
        self.length = u32(21)
        self.header1 = u32(2)
        self.header2 = u32(0)
        self.timecode = f32(float(timecode))
        self.slot_name = hash_name_or_get_hash(slot_name)
        if u2.lstrip() != "0":
            self.u2 = hash_name_or_get_hash(u2)
        else:
            self.u2 = u32(0)
        self.b1 = u8(int(b1))

    def to_binary(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                    self.slot_name, self.u2, self.b1]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff


class FocusCompatibilityEvent:
    arg_count = 3

    def __init__(self, timecode, end_timecode, level):
        self.event_type = u32(18)
        self.length = u32(17)
        self.header1 = u32(1)
        self.header2 = u32(256)
        self.timecode = f32(float(timecode))
        self.end_timecode = f32(float(end_timecode))
        self.level = u8(int(level))

    def to_binary(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.end_timecode, self.level]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff


class GeometryStateChangeEvent:
    arg_count = 3

    def __init__(self, timecode, actor_name, geometry_state_name):
        self.event_type = u32(17)
        self.length = u32(144)
        self.header1 = u32(1)
        self.header2 = u32(86)
        self.timecode = f32(float(timecode))
        self.actor_hash = hash_name_or_get_hash(actor_name)
        geometry_state_name = geometry_state_name.lstrip().encode("ascii")
        self.geometry_state_name = Bytes(get_null_terminated_string(geometry_state_name))

    def to_binary(self):
        serialized = [self.event_type, self.length, self.header1, self.header2, self.timecode,
                      self.actor_hash, self.geometry_state_name]

        serialized_stuff = []
        for value in serialized:
            serialized_stuff.append(value.to_binary())

        return serialized_stuff