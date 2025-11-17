

if "bpy" in locals():
    import importlib
    importlib.reload(colormodels)
    # importlib.reload(tulips3dData)
    importlib.reload(tulips3dGeometry)

else:
    from . import colormodels
    # from . import tulips3dData
    from . import tulips3dGeometry

import bpy
from bpy.props import (
    FloatProperty,
    StringProperty,
    IntProperty,
    EnumProperty,
    CollectionProperty
)

import DataPrepTulips3D as DP

import sys
from time import time

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LogNorm
from scipy.interpolate import interp1d

import mesaPlot as mp



bl_info = {
    "name": "Tulips3D",
    "author": "B.L. de Vries",
    "version": (0, 0, 1),
    "blender": (4, 5, 0),          # <-- target version
    "location": "Properties > Scene",
    "description": "Adds a 3d visualisation of the output of the MESA stellar evolution code.",
    "category": "Object",
}

# Global Keys
key_tulips_data = 'tulips_grid_data'
key_active_profile_key = 'tulips_active_profile_key'
active_time_index = 'active_time_index'


# ######################################################
# CREATING AND LOOP FUNCTIONs
# ######################################################
def create_pieces():
    print()

def update_pieces():
    print()


# ######################################################
# OPERATORS
# ######################################################
# This operator adds the geometry of one "piece" of the star
class OBJECT_OT_add_tulips3d_geo(bpy.types.Operator):
    """Operator to add Tulips3D geometry"""
    bl_idname = "object.tulips3d"
    bl_label = "Create Tulips3D Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.Tulips3DSettingsUI # We pull the current settings from context.scene.simple_geo_settings.

        # Create the geometry of the 3d pie slice
        ob = tulips3dGeometry.make_star_pie(\
            ob_name=settings.ob_name, \
            nr_R=settings.mesh_r_nr_steps, \
            nr_Th=settings.mesh_th_nr_steps, \
            verbose_timing=True)

        # Load the mesa data
        d = DP.load_Data1D_from_pickle(settings.file_path_data1d)

        # Create a dict as a custom property on the object to hold the arrays
        ob[key_tulips_data] = {}
        ob[key_active_profile_key] = d.getGridPropertyLabels()[0]
        ob[active_time_index] = int(0)

        for k in d.getGridPropertyLabels():
            ob[key_tulips_data].update({k:d.getProperty(k)})
        
        update_profile(ob)

        print("Data avaliable: ", d.getGridPropertyLabels(), list(ob[key_tulips_data].keys()))

        return {'FINISHED'}

# ######################################################
# HANDLERS
# ######################################################
def frame_change(scene):
    settings = bpy.context.scene.Tulips3DSettingsUI

    obj = bpy.data.objects[settings.ob_name]#.scale = (s, s, s)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    modul = int(scene.frame_current/len(obj.stellarProperties))
    start_ind = obj.stellarProperties[scene.frame_current-modul*len(obj.stellarProperties)].T_index
    bpy.ops.geometry.color_attribute_render_set(name="energy_ver_col_"+str(int(start_ind)))




# ######################################################
# UI
# ######################################################

class Tulips3DSettingsUI(bpy.types.PropertyGroup):
    """Container for UI‑exposed settings"""
    ob_name : StringProperty(
        name="Object name",
        description="Name of the object in Blender",
        default="Star_Pie",
    )
    
    file_path_data1d_default = '/Users/vries001/Dropbox/0_DATA_BEN/PHYSICS/PROJECTS/tulips3D/example_MESA_data/Data1DFormat/binary.pkl'
    file_path_data1d : StringProperty(
        name="MESA data in Data1D format path",
        description="MESA data in Data1D format path",
        default=file_path_data1d_default,
        subtype="DIR_PATH"
    )

    # type : EnumProperty(
    #     name="Type",
    #     description="What MESA data type to use",
    #     items=[
    #         ('ENERGY',   "Energy",   ""),
    #         ('NEXT',   "Which is next?",   ""),
    #     ],
    #     default='ENERGY',
    # )

    time_index_step : IntProperty(
        name="time_index_step",
        description="Time index step size for animation",
        default=1000,
        # min=3,
        # max=256,
    )

    mesh_r_nr_steps : IntProperty(
        name="Radial #steps mesh",
        description="",
        default=50,
        # min=3,
        # max=256,
    )

    mesh_th_nr_steps : IntProperty(
        name="Theta #steps mesh",
        description="",
        default=50,
        # min=3,
        # max=256,
    )


class VIEW3D_PT_tulips3d_panel(bpy.types.Panel):
    """Panel placed in the Properties editor → Scene tab"""
    bl_label = "Tulips3D"
    bl_idname = "VIEW3D_PT_tulips3d_panel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"          # appears under the Scene tab

    def draw(self, context):
        layout = self.layout
        settings = context.scene.Tulips3DSettingsUI

        col = layout.column()
        col.prop(settings, "ob_name")
        col.prop(settings, "file_path_data1d")
        # col.prop(settings, "ani_type")
        # if settings.ani_type == "STILL":
        # col.prop(settings, "type")
        col.prop(settings, "time_index_step")
        col.prop(settings, "mesh_r_nr_steps")
        col.prop(settings, "mesh_th_nr_steps")

        # col.prop(settings, "shape")
        # col.prop(settings, "size")
        # col.prop(settings, "segments")

        col.separator()
        col.operator("object.tulips3d", icon='MESH_CUBE')




# This is called when the user selects a blender object 
# and it updates which enum options are available in the
# sidebar
def mesaDataProfEnum_callback(scene, context):
    print("SELECTING!!!!!!", bpy.context.selected_objects)
        # context.scene.Tulips3DSettingsUI_sidebar.mesaDataProfEnum, \
        # type(context.scene.Tulips3DSettingsUI_sidebar.mesaDataProfEnum))
    items = []
    # get selection
    selection = bpy.context.selected_objects
    if len(selection) == 1:
        ob = bpy.context.selected_objects[0]
        # Check if the object has mesa profile data attached
        if key_tulips_data in ob.keys():
            for k in ob[key_tulips_data].keys():
                items.append((k, k, ""))

        # Set the enum to the current active data
        # context.scene.Tulips3DSettingsUI_sidebar.mesaDataProfEnum = ob[key_active_profile_key]
    return items

# This is called when the user selects a mesa profile in the sidebar
# and this should this update the geometry
def mesaDataProfEnum_update(scene, context):
    selected_profile = context.object.mesaProfileEnum#context.scene.Tulips3DSettingsUI_sidebar.mesaDataProfEnum
    print(selected_profile)
    selected_time_index = 0.

    selected = context.selected_objects
    if len(selected) == 1:
        ob = selected[0]
        if  selected_profile != ob[key_active_profile_key] or \
            selected_time_index != ob[active_time_index]:

            ob[key_active_profile_key] = selected_profile
            ob[active_time_index] = int(0)
            
            update_profile(ob)
        print("mesaDataProfEnum_update: STILL NEED TO USE TIME INDEX!!")


def update_profile(ob):
    print("Update", ob[key_active_profile_key], ob[active_time_index])
    r, v = ob[key_tulips_data][ob[key_active_profile_key]][ob[active_time_index]]
    tulips3dGeometry.make_vertex_colors(np.array(r), np.array(v), ob.name)


def obname_callback(scene, context):
    selection = bpy.context.selected_objects
    if len(selection)>0:
        return selection[0].name
    else:
        return ""

def update_obname(self, context):
        print("ASDASDA", self.ob_name)
        if self.ob_name is None:
            return
        # o = self.ob_name.add()
        # o.name = self.ob_name.name

        selection = context.selected_objects
        if len(selection)>0:
            self.ob_name = selection[0].name

# class Tulips3DSettingsUI_sidebar(bpy.types.PropertyGroup):
#     """Container for UI‑exposed settings"""
#     mesaDataProfEnum : EnumProperty(
#         name="MESA data profiles",
#         description="",
#         items=mesaDataProfEnum_callback,
#         update=mesaDataProfEnum_update
#         )

    

class SIDEBAR_PT_tulips3d_panel(bpy.types.Panel):
    """Panel placed in the Properties editor → Scene tab"""
    bl_label = "SIDEBAR_PT_tulips3d_panel"
    bl_idname = "SIDEBAR_PT_tulips3d_panel"
    # bl_space_type = "PROPERTIES"
    # bl_region_type = "WINDOW"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    # bl_context = "scene"          # appears under the Scene tab

    def draw(self, context):
        layout = self.layout
        # settings = context.scene.Tulips3DSettingsUI_sidebar

        if len(bpy.context.selected_objects) > 0:
            ob = bpy.context.selected_objects[0]

        col = layout.column()
        col.label(text = "Object: "+str(ob.name))
        # col.label(text = "Active profile: "+ob[key_active_profile_key])

        # col.prop(settings, "ob_name")
        # col.prop(settings, "mesaDataProfEnum")
        col.separator(factor=1.0, type='LINE')
        col.label(text = "MESA Profile: ")
        col.prop(context.object, "mesaProfileEnum")

        
        # # col.prop(settings, "ani_type")
        # # if settings.ani_type == "STILL":
        # col.prop(settings, "type")
        # col.prop(settings, "time_index_step")
        # col.prop(settings, "mesh_r_nr_steps")
        # col.prop(settings, "mesh_th_nr_steps")

        # col.prop(settings, "shape")
        # col.prop(settings, "size")
        # col.prop(settings, "segments")

        # col.separator()
        # col.operator("object.tulips3d", icon='MESH_CUBE')


# ######################################################
# DATA CLASSES - BLENDER
# ######################################################
class StellarEvolutionProperties(bpy.types.PropertyGroup): #FloatItem
    """Stellar evolution data saved on an object using a PropertyGroup"""
    R_star: FloatProperty(name="Value")
    T_index: FloatProperty(name="Value")

# ######################################################
# REGISTERING AND STUFF
# ######################################################
classes = (
    Tulips3DSettingsUI,
    # Tulips3DSettingsUI_sidebar,
    OBJECT_OT_add_tulips3d_geo,
    VIEW3D_PT_tulips3d_panel,
    SIDEBAR_PT_tulips3d_panel,
    StellarEvolutionProperties
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Attach the PropertyGroup to the scene
    bpy.types.Scene.Tulips3DSettingsUI = bpy.props.PointerProperty(type=Tulips3DSettingsUI)
    # bpy.types.Scene.Tulips3DSettingsUI_sidebar = bpy.props.PointerProperty(type=Tulips3DSettingsUI_sidebar)

    # The enum needs to be linked to the object (not scene), to update propertly
    # https://harlepengren.com/how-to-make-a-dynamic-dropdown-in-blender-python/
    bpy.types.Object.mesaProfileEnum = bpy.props.EnumProperty(name="",description="a dynamic list",\
        items=mesaDataProfEnum_callback,\
        update=mesaDataProfEnum_update)


    # Attach an empty CollectionProperty to every Object
    bpy.types.Object.stellarProperties = CollectionProperty(
        type=StellarEvolutionProperties,
        name="Stellar evolution data",
        description="Stellar evolution properties (like t and R) as function of time"
    )

    bpy.app.handlers.frame_change_pre.append(frame_change)


def unregister():
    # Remove the property first
    del bpy.types.Scene.Tulips3DSettingsUI
    # del bpy.types.Scene.Tulips3DSettingsUI_sidebar
    del bpy.types.Object.stellarProperties

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    bpy.app.handlers.frame_change_pre.remove(frame_change)

# if __name__ == "__main__":
#     register()