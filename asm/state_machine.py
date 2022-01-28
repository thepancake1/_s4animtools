import bpy
from bpy.props import IntProperty, CollectionProperty, FloatProperty, StringProperty, EnumProperty, BoolProperty
from bpy.types import PropertyGroup, Operator

class ActorProperties(PropertyGroup):
    name: StringProperty(name="Actor Name")
    type: EnumProperty(name = "Actor Type", items=(('Sim', 'Sim', ""), ('Object', 'Object', ""), ('Prop', 'Prop', ""),))
    master : BoolProperty(name = "Master", default=False)
    virtual : BoolProperty(name = "Virtual", default=False)



class LIST_OT_NewActor(Operator):
    bl_idname = "actor.new"
    bl_label = "Add a new item"

    def execute(self, context):
        context.object.actors.add()
        return {'FINISHED'}

class LIST_OT_DeleteActor(Operator):
    bl_idname = "actor.delete"
    bl_label = "Delete an item"

    def execute(self, context):
        context.object.actors.remove(context.object.actor_idx)
        context.object.actor_idx = max(len(context.object.actors) - 1, 0)
        return {'FINISHED'}

class LIST_OT_MoveActor(Operator):
    bl_idname = "actor.move"
    bl_label = "Move an actor"

    direction: bpy.props.EnumProperty(items=(('UP', 'Up', ""), ('DOWN', 'Down', ""),))

    def execute(self, context):
        if self.direction == "UP":
            context.object.actor_idx -= 1
        elif self.direction == "DOWN":
            context.object.actor_idx += 1
        context.object.actor_idx = min(max(context.object.actor_idx, 0), len(context.object.actors) - 1)
        return {'FINISHED'}


class ActorPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Actor Panel"
    bl_idname = "OBJECT_PT_actor_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout

        obj = context.object
        box = layout.box()
        box_row = box.row(align=True)
        row = box_row

        if obj.actor_idx >= 0 and obj.actors:
            for idx, item in enumerate(obj.actors):
                row = row.column()
                sub = row.row(align=True)
                sub.scale_x = 1

                if idx == obj.actor_idx:
                    sub.label(text="•Actor Name")
                else:
                    sub.label(text="Actor Name")

                sub.prop(item, "name", text="")
                sub = row.row(align=True)

                sub.label(text="        Type")
                sub.prop(item, "type", text="")
                sub = row.row(align=True)

                sub.label(text="        Master")
                sub.prop(item, "master", text="")

                sub.label(text="        Virtual")
                sub.prop(item, "virtual", text="")

        row = layout.row()
        row.operator('actor.new', text='New')
        row.operator('actor.move', text='Down').direction = 'DOWN'
        row.operator('actor.move', text='Up').direction = 'UP'
        row.operator('actor.delete', text='Delete')