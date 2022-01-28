def recursive_bone_finalize(bone):
    current_sequence_count = 1  # This affects the actual IK translation and rotation offset data
    for channel_name, channel_bundle in animated_bones[bone.name].items():
        for channel_type, channel_data in channel_bundle.items():
            # Don't need to save channel if nothing is in it
            if len(channel_data) == 0:
                continue

            all_frame_data = {}
            current_channel = None
            if channel_type == "TRANSLATION":
                current_channel = _s4animtools.channels.translation_channel.TranslationChannel(bone.name, 18, 1)
            elif channel_type == "ORIENTATION":
                current_channel = _s4animtools.channel.Channel(bone.name, 20, 2)

            if "IK" in channel_name:
                if channel_type == "TRANSLATION":
                    current_channel = _s4animtools.channels.translation_channel.TranslationChannel(bone.name, 18, 23 + (
                            current_sequence_count * 2))
                elif channel_type == "ORIENTATION":
                    current_channel = _s4animtools.channel.Channel(bone.name, 20,
                                                                   (24 + current_sequence_count * 2))
            finalize_channels(all_frame_data, channel_data, current_channel)
        if "IK" in channel_name:
            current_sequence_count += 1

    for bone in bone.children:
        recursive_bone_finalize(bone)
