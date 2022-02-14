from enum import IntEnum


class ChannelType(IntEnum):
    ChannelType_Unknown = 0,
    F1 = 1,
    F2 = 2,
    F3 = 3,
    F4 = 4,

    F1_Normalized = 5,
    F2_Normalized = 6,
    F3_Normalized = 7,
    F4_Normalized = 8,

    F1_Zero = 9,
    F2_Zero = 10,
    F3_Zero = 11,
    F4_Zero = 12,

    F1_One = 13,
    F2_One = 14,
    F3_One = 15,
    F4_One = 16,

    F4_QuaternionIdentity = 17,

    F3_HighPrecisionNormalized = 18,
    F4_HighPrecisionNormalized_Quaternion = 19,
    F4_SuperHighPrecision_Quaternion = 20,
    F3_HighPrecisionNormalized_Quaternion = 21

class SubChannelType(IntEnum):
    SubTarget_Unknown = 0,
    Translation  = 1,
    Orientation = 2,
    Scale = 3,

    IK_TargetWeight_World = 14,
    IK_TargetWeight_1 = 15,
    IK_TargetWeight_2 = 16,
    IK_TargetWeight_3 = 17,
    IK_TargetWeight_4 = 18,
    IK_TargetWeight_5 = 19,
    IK_TargetWeight_6 = 20.
    IK_TargetWeight_7 = 21,
    IK_TargetWeight_8 = 22.
    IK_TargetWeight_9 = 23,
    IK_TargetWeight_10 = 24,

    IK_TargetOffset_Translation_World = 25
    IK_TargetOffset_Orientation_World = 26
    IK_TargetOffset_Translation_1 = 27
    IK_TargetOffset_Orientation_1 = 28
    IK_TargetOffset_Translation_2 = 29
    IK_TargetOffset_Orientation_2 = 30
    IK_TargetOffset_Translation_3 = 31
    IK_TargetOffset_Orientation_3 = 32
    IK_TargetOffset_Translation_4 = 33
    IK_TargetOffset_Orientation_4 = 34
    IK_TargetOffset_Translation_5 = 35
    IK_TargetOffset_Orientation_5 = 36
    IK_TargetOffset_Translation_6 = 37
    IK_TargetOffset_Orientation_6 = 38
    IK_TargetOffset_Translation_7 = 39
    IK_TargetOffset_Orientation_7 = 40
    IK_TargetOffset_Translation_8 = 41
    IK_TargetOffset_Orientation_8 = 42
    IK_TargetOffset_Translation_9 = 43
    IK_TargetOffset_Orientation_9 = 44
    IK_TargetOffset_Translation_10 = 45
    IK_TargetOffset_Orientation_10 = 46