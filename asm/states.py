import bpy
from bpy.props import IntProperty, CollectionProperty, FloatProperty, StringProperty, EnumProperty, BoolProperty
from bpy.types import PropertyGroup, Operator

def actors_enum(self, context):
    items = context.object.actors
    actors_list = []
    for item in items:
        actors_list.append((item.name, item.name, ""))
    return actors_list

def potential_actors_enum(self, context):
    items = context.object.actors
    actors_list = [("-", "-", ""), ("*", "*", "")]
    for item in items:
        actors_list.append((item.name, item.name, ""))
    return actors_list


def states_enum(self, context):
    items = context.object.states
    states_list = [("entry", "entry", ""),
                   ("exit", "exit", "")]
    for item in items:
        states_list.append((item.name, item.name, ""))
    return states_list
class PostureProperties(PropertyGroup):
    actor1: EnumProperty(name="Actor", items=actors_enum)
    actor2: EnumProperty(name="Actor", items=potential_actors_enum)

    posture_name: StringProperty(name="Posture Name")
    posture_family: StringProperty(name="Posture Family")
    compatibility: EnumProperty(items=(('FullBody', 'FullBody', ""), ('UpperBody', 'UpperBody', ""),))
    carry_left: EnumProperty(name="Carry Left", items=potential_actors_enum)
    carry_right: EnumProperty(name="Carry Right", items=potential_actors_enum)
    surface: EnumProperty(name="Carry Surface", items=potential_actors_enum)

class ControllerProperties(PropertyGroup):
    name: StringProperty(name="Clip Name")
    target: EnumProperty(name="Actor", items=actors_enum)
    focus: EnumProperty(name="Focus Level",
                        items=(('Full Body', 'Full Body', ""), ('Head Only', 'Head Only', ""), ('None', 'None', ""),
                               ('Undefined', 'Undefined', ""),))
    mask: StringProperty(name="Mask")
    track: EnumProperty(name="Track", items=(('low', 'low', ""), ('normal', 'normal', ""),
                                                   ('normalplus', 'normalplus', ""),))
    blendin: FloatProperty(name="Blend In")
    blendout: FloatProperty(name="Blend Out")


class StateProperties(PropertyGroup):
    name: StringProperty(name="State Name")
    public: BoolProperty(name="Public", default=False)
    skippable: BoolProperty(name="Skippable", default=False)
    interrupt_this: BoolProperty(name="Interrupt This", default=False)

    focus: EnumProperty(name="Focus Level", items=(('Full Body', 'Full Body', ""), ('Head', 'Head', ""), ('None', 'None', ""),
                                                     ('Undefined', 'Undefined', ""),))
    facial_overlays: BoolProperty(name="Facial Overlays", default=False)
    tail_overlays: BoolProperty(name="Tail Overlays", default=False)
    controllers: CollectionProperty(type=ControllerProperties)

class StateConnections(PropertyGroup):
    previous_state: EnumProperty(name="States", items=states_enum)
    next_state: EnumProperty(name="States", items=states_enum)


class LIST_OT_NewState(Operator):
    bl_idname = "state.new"
    bl_label = "Add a new item"

    def execute(self, context):
        context.object.states.add()
        return {'FINISHED'}


class LIST_OT_NewController(Operator):
    bl_idname = "controller.new"
    bl_label = "Add a new item"

    def execute(self, context):
        try:
            context.object.states[context.object.state_idx].controllers =  CollectionProperty(type=ControllerProperties)
        except Exception as e:
            print(e)
        context.object.states[context.object.state_idx].controllers.add()
        return {'FINISHED'}


class LIST_OT_RemoveController(Operator):
    bl_idname = "controller.delete"
    bl_label = "Add a new item"

    def execute(self, context):
        try:
            context.object.states[context.object.state_idx].controllers =  CollectionProperty(type=ControllerProperties)
        except Exception as e:
            print(e)
        context.object.states[context.object.state_idx].controllers.remove(context.object.controller_idx)
        context.object.state_idx = min(max(context.obj.controller_idx, 0), len(context.object.controller_idx) - 1)
        return {'FINISHED'}


class LIST_OT_DeleteState(Operator):
    bl_idname = "state.delete"
    bl_label = "Delete an item"

    def execute(self, context):
        context.object.states.remove(context.object.state_idx)
        context.object.state_idx = max(len(context.object.state_idx) - 1, 0)

        return {'FINISHED'}

class LIST_OT_MoveState(Operator):
    bl_idname = "state.move"
    bl_label = "Move an item"

    direction: bpy.props.EnumProperty(items=(('UP', 'Up', ""), ('DOWN', 'Down', ""),))

    def execute(self, context):
        context.object.controller_idx = 0
        if self.direction == "UP":
            context.object.state_idx -= 1
        elif self.direction == "DOWN":
            context.object.state_idx += 1
        context.object.state_idx = min(max(context.object.state_idx, 0), len(context.object.states) - 1)
        return {'FINISHED'}

class LIST_OT_MoveControllerState(Operator):
    bl_idname = "controller.move"
    bl_label = "Move an item"

    direction: bpy.props.EnumProperty(items=(('UP', 'Up', ""), ('DOWN', 'Down', ""),))

    def execute(self, context):
        if self.direction == "UP":
            context.object.controller_idx -= 1
        elif self.direction == "DOWN":
            context.object.controller_idx += 1
        context.object.controller_idx = min(max(context.object.controller_idx, 0), len(context.object.states[context.object.state_idx].controllers) - 1)
        return {'FINISHED'}

class PosturePanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Posture Panel"
    bl_idname = "OBJECT_PT_posture_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout

        obj = context.object
        box = layout.box()
        box_row = box.row(align=True)
        row = box_row

        if obj.postures:
            for idx, item in enumerate(obj.postures):
                row = row.column()
                sub = row.row(align=True)
                sub.scale_x = 1
                sub.label(text="actor1")

                sub.prop(item, "actor1", text="")
                sub.label(text="actor2")

                sub.prop(item, "actor2", text="")

                sub.label(text="posture_name")
                sub.prop(item, "posture_name", text="")

                sub.label(text="posture_family")
                sub.prop(item, "posture_family", text="")
                sub = row.row(align=True)

                sub.label(text="compatibility")
                sub.prop(item, "compatibility", text="")
                sub.label(text="carry_left")
                sub.prop(item, "carry_left", text="")
                sub.label(text="carry_right")
                sub.prop(item, "carry_right", text="")
                sub.label(text="surface")
                sub.prop(item, "surface", text="")
        row.operator('posture.new', text='New Controller')
        row.operator('posture.delete', text='Delete Controller')
        row.operator('posture.move', text='Down').direction = 'DOWN'
        row.operator('posture.move', text='Up').direction = 'UP'

class StatePanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "States Panel"
    bl_idname = "OBJECT_PT_state_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout

        obj = context.object
        box = layout.box()
        box_row = box.row(align=True)
        row = box_row

        if obj.state_idx >= 0 and obj.states:
            for idx, item in enumerate(obj.states):
                row = row.column()
                sub = row.row(align=True)
                sub.scale_x = 1

                if idx == obj.state_idx:
                    sub.label(text="•State Name")
                else:
                    sub.label(text="State Name")

                sub.prop(item, "name", text="")
                sub = row.row(align=True)

                sub.label(text="        Public")
                sub.prop(item, "public", text="")
                sub = row.row(align=True)

                sub.label(text="        Skippable")
                sub.prop(item, "skippable", text="")
                sub = row.row(align=True)
                sub.label(text="        Interrupt This")
                sub.prop(item, "interrupt_this", text="")
                sub = row.row(align=True)
                sub.label(text="        Focus")
                sub.prop(item, "focus", text="")
                sub = row.row(align=True)

                sub.label(text="        Facial Overlays")
                sub.prop(item, "facial_overlays", text="")
                sub = row.row(align=True)

                sub.label(text="        Tail Overlays")
                sub.prop(item, "tail_overlays", text="")
                sub = row.row()


                sub = row.row()
                if hasattr(item, "controllers"):
                    for idx, controller in enumerate(item.controllers):
                        if idx == context.object.controller_idx:
                            sub.label(text="             •Controller")
                            sub.prop(controller, "name", text="")
                            sub = row.row(align=True)
                        else:
                            sub.label(text="             Controller")
                            sub.prop(controller, "name", text="")
                            sub = row.row(align=True)
                        sub.label(text="             Target")
                        sub.prop(controller, "target", text="")
                        sub = row.row(align=True)
                        sub.label(text="             Track")

                        sub.prop(controller, "track", text="")
                        sub = row.row(align=True)
                        sub.label(text="             Blend In")
                        sub.prop(controller, "blendin", text="")

                        sub.label(text="             Blend out")
                        sub.prop(controller, "blendout", text="")
                        sub = row.row(align=True)

        row = layout.row()
        row.operator('state.new', text='New')
        row.operator('state.move', text='Down').direction = 'DOWN'
        row.operator('state.move', text='Up').direction = 'UP'
        row.operator('state.delete', text='Delete')
        row = layout.row()

        row.operator('controller.new', text='New Controller')
        row.operator('controller.delete', text='Delete Controller')
        row.operator('controller.move', text='Down').direction = 'DOWN'
        row.operator('controller.move', text='Up').direction = 'UP'
        row = layout.row()


        if obj.state_connection_idx >= 0 and obj.states:
            for idx, item in enumerate(obj.state_connections):
                row = row.column()

                sub = row.row(align=True)
                sub.scale_x = 1

                if idx == obj.state_connection_idx:
                    sub.label(text="•State Connection")
                else:
                    sub.label(text="State Connection")
                sub = row.row()

                sub.label(text="        Previous State")
                sub.prop(item, "previous_state", text="")
                sub.label(text="        Next State")
                sub.prop(item, "next_state", text="")

        row = layout.row()
        row.operator('state_connection.new', text='New State Connection')
        row.operator('state_connection.delete', text='Delete State Connection')
        row.operator('state_connection.move', text='Down').direction = 'DOWN'
        row.operator('state_connection.move', text='Up').direction = 'UP'
        row.operator("s4animtools.export_animation_state_machine", text="Export Animation State Machine")
class LIST_OT_NewPosture(Operator):
    bl_idname = "posture.new"
    bl_label = "Add a new item"

    def execute(self, context):
        context.object.postures.add()
        return {'FINISHED'}
class LIST_OT_DeletePosture(Operator):
    bl_idname = "posture.delete"
    bl_label = "Delete an item"

    def execute(self, context):
        context.object.postures.remove(context.object.posture_idx)
        context.object.posture_idx = max(len(context.object.posture_idx) - 1, 0)

        return {'FINISHED'}

class LIST_OT_MovePosture(Operator):
    bl_idname = "posture.move"
    bl_label = "Move an item"

    direction: bpy.props.EnumProperty(items=(('UP', 'Up', ""), ('DOWN', 'Down', ""),))

    def execute(self, context):
        context.object.controller_idx = 0
        if self.direction == "UP":
            context.object.posture_idx -= 1
        elif self.direction == "DOWN":
            context.object.posture_idx += 1
        context.object.posture_idx = min(max(context.object.posture_idx, 0), len(context.object.postures) - 1)


class LIST_OT_NewStateConnection(Operator):
    bl_idname = "state_connection.new"
    bl_label = "Add a new item"

    def execute(self, context):
        context.object.state_connections.add()
        return {'FINISHED'}
class LIST_OT_DeleteStateConnection(Operator):
    bl_idname = "state_connection.delete"
    bl_label = "Delete an item"

    def execute(self, context):
        context.object.states.remove(context.object.state_connection_idx)
        context.object.state_connection_idx = max(len(context.object.state_connection_idx) - 1, 0)

        return {'FINISHED'}

class LIST_OT_MoveStateConnection(Operator):
    bl_idname = "state_connection.move"
    bl_label = "Move an item"

    direction: bpy.props.EnumProperty(items=(('UP', 'Up', ""), ('DOWN', 'Down', ""),))

    def execute(self, context):
        if self.direction == "UP":
            context.object.state_connection_idx -= 1
        elif self.direction == "DOWN":
            context.object.state_connection_idx += 1
        context.object.state_connection_idx = min(max(context.object.state_connection_idx, 0), len(context.object.state_connections) - 1)
        return {'FINISHED'}
