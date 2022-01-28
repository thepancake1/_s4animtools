import math
import os.path

from mathutils import Matrix
import bpy

class CopyLeftSideAnimationToRightSide(bpy.types.Operator):
    bl_idname = "s4animtools.copy_left_side"
    bl_label = "Copy Left Side Animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        action = obj.animation_data.action
        d = ["_bind_DB_blanket_Top_L_", "_bind_DB_blanket_Mid_L_", "_bind_DB_blanket_Bottom_L_",
             "_bind_DB_OpacityPanel_L_", "_bind_DB_blanket_MakeBedFront_L_", "_bind_DB_blanket_MakeBedMid_L_"]
        for group in action.groups:
          #  if group.name.replace("_R_", "_L_") in d:
            oldname = group.name

            group.name = group.name.replace("_R_", "_R_unused").replace("_r_", "_r_unused")
            for fcurve in group.channels:
                fcurve.data_path = fcurve.data_path.replace(oldname, oldname.replace("_R_", "_R_unused").replace("_r_", "_r_unused"))



        for group in action.groups:
            #if group.name in d:
            oldname = group.name

            group.name = group.name.replace("_L_", "_R_temp").replace("_l_", "_r_temp")
            for fcurve in group.channels:
                fcurve.data_path = fcurve.data_path.replace(oldname, oldname.replace("_L_", "_R_temp").replace("_l_", "_r_temp"))

        for group in action.groups:
           # if group.name.endswith("temp"):
            oldname = group.name
            group.name = group.name.replace("temp", "")
            for fcurve in group.channels:
                fcurve.data_path = fcurve.data_path.replace(oldname, group.name)

               # if "location" in fcurve.data_path and fcurve.array_index == 2:
               #     print("test")
               #     for keyframe in fcurve.keyframe_points:
               #         current_value = keyframe.co[1]
               #         keyframe.co[1] = current_value * -1
               #         print(current_value)

                if "rotation_quaternion" in fcurve.data_path and fcurve.array_index == 2 or fcurve.array_index == 3:
                    print("test")
                    for keyframe in fcurve.keyframe_points:
                        current_value = keyframe.co[1]
                        keyframe.co[1] = current_value * -1
                        print(current_value)

        return {"FINISHED"}
class CopyLeftSideAnimationToRightSideSim(bpy.types.Operator):
    bl_idname = "s4animtools.copy_left_side_sim"
    bl_label = "Copy Left Side Animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        action = obj.animation_data.action
        d = ["_bind_DB_blanket_Top_L_", "_bind_DB_blanket_Mid_L_", "_bind_DB_blanket_Bottom_L_",
             "_bind_DB_OpacityPanel_L_", "_bind_DB_blanket_MakeBedFront_L_", "_bind_DB_blanket_MakeBedMid_L_"]
       #for group in action.groups:
       #  #  if group.name.replace("_R_", "_L_") in d:
       #    oldname = group.name

       #    group.name = group.name.replace("_R_", "_R_unused").replace("_r_", "_r_unused")
       #    for fcurve in group.channels:
       #        fcurve.data_path = fcurve.data_path.replace(oldname, oldname.replace("_R_", "_R_unused").replace("_r_", "_r_unused"))



        for group in action.groups:
            #if group.name in d:
            oldname = group.name


            if "_L_" in group.name or "_l_" in group.name:
                group.name = group.name.replace("_L_", "_R_temp").replace("_l_", "_r_temp")
            elif "_R_" in group.name or "_r_" in group.name:
                group.name = group.name.replace("_R_", "_L_temp").replace("_r_", "_l_temp")

            if "temp" not in group.name:
                group.name = group.name + "temp"
            for fcurve in group.channels:
                fcurve.data_path = fcurve.data_path.replace(oldname,group.name)

        for group in action.groups:
            oldname = group.name
            group.name = group.name.replace("temp", "")
            for fcurve in group.channels:
                fcurve.data_path = fcurve.data_path.replace(oldname, group.name)

                if "rotation_quaternion" in fcurve.data_path:
                    if fcurve.array_index == 1 or fcurve.array_index == 2:
                        for keyframe in fcurve.keyframe_points:
                            current_value = keyframe.co[1]
                            keyframe.co[1] = current_value * -1
                            print(current_value)


                if "location" in fcurve.data_path:
                    if fcurve.array_index == 2:
                        for keyframe in fcurve.keyframe_points:
                            current_value = keyframe.co[1]
                            keyframe.co[1] = current_value * -1
                            print(current_value)

        return {"FINISHED"}
class CopySelectedLeftSideToRightSide(bpy.types.Operator):
    bl_idname = "s4animtools.copy_left_side_sim_selected"
    bl_label = "Copy Left Side Animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        action = obj.animation_data.action

        selected_bones = bpy.context.selected_pose_bones
        selected_bones = [x.name for x in selected_bones]
        for item in selected_bones[:]:
            selected_bones.append(item.replace("_L_", "_R_").replace("_l_", "_r_"))
        print(selected_bones)

        for group in action.groups:

            oldname = group.name


            if "_L_" in group.name or "_l_" in group.name:
                group.name = group.name.replace("_L_", "_R_temp").replace("_l_", "_r_temp")
            elif "_R_" in group.name or "_r_" in group.name:
                group.name = group.name.replace("_R_", "_L_temp").replace("_r_", "_l_temp")
            if group.name in selected_bones:

                if "temp" not in group.name:
                    group.name = group.name + "temp"
                for fcurve in group.channels:
                    fcurve.data_path = fcurve.data_path.replace(oldname,group.name)

        for group in action.groups:
           # if group.name.endswith("temp"):
            oldname = group.name
            group.name = group.name.replace("temp", "")
            if group.name in selected_bones:
                for fcurve in group.channels:
                    fcurve.data_path = fcurve.data_path.replace(oldname, group.name)
                    print(fcurve.data_path)


                    if "rotation_quaternion" in fcurve.data_path:
                        if fcurve.array_index == 1 or fcurve.array_index == 2:
                            print("test")
                            for keyframe in fcurve.keyframe_points:
                                current_value = keyframe.co[1]
                                keyframe.co[1] = current_value * -1
                                print(current_value)


                    if "location" in fcurve.data_path:
                        if fcurve.array_index == 2:
                            for keyframe in fcurve.keyframe_points:
                                current_value = keyframe.co[1]
                                keyframe.co[1] = current_value * -1
                                print(current_value)

        return {"FINISHED"}
