
import bpy
class OT_S4ANIMTOOLS_CreateClipData(bpy.types.Operator):
    """Add roots to the list."""
    bl_idname = "s4animtools.create_clip_data"
    bl_label = "Create new clip data"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        context.scene.clips.add()
        context.scene.clips[-1].clip_name = str(len(context.scene.clips))


        return {'FINISHED'}


class OT_S4ANIMTOOLS_InitializeThumbnails(bpy.types.Operator):
    bl_idname = "s4animtools.initialize_thumbnails"
    bl_label = "Initialize Thumbnails"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        actors = []
        for idx, clip in enumerate(context.scene.clips):
            if clip.clip_name == "":
                clip.clip_name = str(idx + 1)
        for potential_actor in context.scene.objects:
            if potential_actor.is_s4_actor and potential_actor.is_enabled_for_animation:
                actors.append(potential_actor)
        for actor in actors:
            for clip in context.scene.clips:
                formatted_clip_name = get_formatted_clip_name(clip.clip_name, actor.rig_name)
                if formatted_clip_name not in bpy.data.textures:
                    tex = bpy.data.textures.new(formatted_clip_name, 'IMAGE')
                else:
                    tex = bpy.data.textures[formatted_clip_name]

                if formatted_clip_name not in bpy.data.images:
                    img = bpy.data.images.new(formatted_clip_name, 64, 64)
                else:
                    img = bpy.data.images[formatted_clip_name]
                tex.image = img
        return {'FINISHED'}


def get_formatted_clip_name(clip_name, actor_name):
    return "{}_{}".format(clip_name, actor_name)
