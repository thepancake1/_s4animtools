def is_slot_bone(bone):
    return "slot" in bone.name.lower()


def is_cas_bone(bone):
    return "cas" in bone.name.lower()


def is_left_bone(bone):
    return "_l_" in bone.name.lower()


def is_right_bone(bone):
    return "_r_" in bone.name.lower()


def is_middle_bone(bone):
    if is_left_bone(bone):
        return False
    if is_right_bone(bone):
        return False
    return True


def is_mouth(bone):
    if bone.parent is None:
        return False
    if bone.parent.name == "b__CAS_LowerMouthArea__":
        return True
    if bone.parent.name == "b__CAS_UpperMouthArea__":
        return True
    return False


def check_if_finger_bone(bone):
    if bone.parent is not None:
        if "hand" in bone.parent.name.lower():
            return True
        if bone.parent.parent is not None:
            if "hand" in bone.parent.parent.name.lower():
                return True

            if bone.parent.parent.parent is not None:

                if "hand" in bone.parent.parent.parent.name.lower():
                    print(bone.name)
                    return True
    return False


def is_left_pinky_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "pinky" in bone.name.lower() and is_left_bone(bone)


def is_left_ring_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "ring" in bone.name.lower() and is_left_bone(bone)


def is_left_mid_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "mid" in bone.name.lower() and is_left_bone(bone)


def is_left_index_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "index" in bone.name.lower() and is_left_bone(bone)


def is_left_thumb_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "thumb" in bone.name.lower() and is_left_bone(bone)


def is_first_left_finger_joint(bone):
    if is_left_pinky_bone(bone) or is_left_ring_bone(bone) or is_left_mid_bone(bone) or is_left_index_bone(
            bone) or is_left_thumb_bone(bone):
        if "0" in bone.name:
            return True

    return False


def is_second_left_finger_joint(bone):
    if is_left_pinky_bone(bone) or is_left_ring_bone(bone) or is_left_mid_bone(bone) or is_left_index_bone(
            bone) or is_left_thumb_bone(bone):
        if "1" in bone.name:
            return True

    return False


def is_third_left_finger_joint(bone):
    if is_left_pinky_bone(bone) or is_left_ring_bone(bone) or is_left_mid_bone(bone) or is_left_index_bone(
            bone) or is_left_thumb_bone(bone):
        if "2" in bone.name:
            return True

    return False


def is_left_finger_joint(bone):
    if is_left_pinky_bone(bone) or is_left_ring_bone(bone) or is_left_mid_bone(bone) or is_left_index_bone(
            bone) or is_left_thumb_bone(bone):
        return True

    return False


def is_right_pinky_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "pinky" in bone.name.lower() and is_right_bone(bone)


def is_right_ring_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "ring" in bone.name.lower() and is_right_bone(bone)


def is_right_mid_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "mid" in bone.name.lower() and is_right_bone(bone)


def is_right_index_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "index" in bone.name.lower() and is_right_bone(bone)


def is_right_thumb_bone(bone):
    if not check_if_finger_bone(bone):
        return False
    return "thumb" in bone.name.lower() and is_right_bone(bone)


def is_first_right_finger_joint(bone):
    if is_right_pinky_bone(bone) or is_right_ring_bone(bone) or is_right_mid_bone(bone) or is_right_index_bone(
            bone) or is_right_thumb_bone(bone):
        if "0" in bone.name:
            return True

    return False


def is_second_right_finger_joint(bone):
    if is_right_pinky_bone(bone) or is_right_ring_bone(bone) or is_right_mid_bone(bone) or is_right_index_bone(
            bone) or is_right_thumb_bone(bone):
        if "1" in bone.name:
            return True

    return False


def is_third_right_finger_joint(bone):
    if is_right_pinky_bone(bone) or is_right_ring_bone(bone) or is_right_mid_bone(bone) or is_right_index_bone(
            bone) or is_right_thumb_bone(bone):
        if "2" in bone.name:
            return True

    return False


def is_right_finger_joint(bone):
    if is_right_pinky_bone(bone) or is_right_ring_bone(bone) or is_right_mid_bone(bone) or is_right_index_bone(
            bone) or is_right_thumb_bone(bone):
        return True

    return False
