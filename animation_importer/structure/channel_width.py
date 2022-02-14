from S4ClipThing.structure.channel_type import ChannelType, SubChannelType

def GetTotalBitsForChannel(channel):
    return GetWidthForChannelType(channel) * GetCountForChannelType(channel)


def GetValuesPackedIntoVariable(channel):
    if GetWidthForChannelType(channel) == 4:
        return 1
    return 1


def GetCountForChannelType(channel):
    if channel == ChannelType.F1 or channel == ChannelType.F1_Normalized or channel == ChannelType.F3_HighPrecisionNormalized:
        return 1

    if channel == ChannelType.F2 or channel == ChannelType.F2_Normalized:
        return 2

    if channel == ChannelType.F3 or channel == ChannelType.F3_Normalized:
        return 3

    if channel == ChannelType.F4 or channel == ChannelType.F4_Normalized:
        return 4

    if channel == ChannelType.F4_SuperHighPrecision_Quaternion or channel == ChannelType.F4_HighPrecisionNormalized_Quaternion\
            or channel == ChannelType.F3_HighPrecisionNormalized_Quaternion:
        return 4

    return 0

def GetWidthForChannelType(channel):

    width_0 = [ChannelType.F1_Zero, ChannelType.F2_Zero, ChannelType.F3_Zero,
               ChannelType.F4_Zero, ChannelType.F1_One, ChannelType.F2_One, ChannelType.F3_One,
               ChannelType.F4_One, ChannelType.F4_QuaternionIdentity]

    width_1 = [ChannelType.F1_Normalized, ChannelType.F2_Normalized,
               ChannelType.F3_Normalized, ChannelType.F4_Normalized]

    width_2 = [ChannelType.F1, ChannelType.F2, ChannelType.F3, ChannelType.F4, ChannelType.F4_SuperHighPrecision_Quaternion]

    width_4 = [ChannelType.F3_HighPrecisionNormalized, ChannelType.F3_HighPrecisionNormalized_Quaternion,]

    # size in bytes
    if channel in width_0:
        return 0
    if channel in width_1:
        return 1
    if channel in width_2:
        return 2
    if channel in width_4:
        return 4


    return -1