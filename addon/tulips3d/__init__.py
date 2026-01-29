

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

# OBJECT KEYS TO TRACK
key_ob_DataPrepTulips3D_data = 'tulips_grid_data' # This holds the DataPrepTulips3D dict
key_ob_active_data_label = 'tulips_active_profile_key' # Label of the currently shown data 
key_ob_active_time_index = 'active_time_index' # Currently shown time index

key_blender_ob_data_dict = "MESA_data_dict"


# Keys of the dict coming from the DataPrepTulips3D
key_DataPrepTulips3D_prof_labels = "prof_labels"
key_DataPrepTulips3D_r_resolution = "r_resolution"
key_DataPrepTulips3D_t_resolution = "t_resolution"
key_DataPrepTulips3D_data_prof_t_r = "data_prof_t_r"
key_DataPrepTulips3D_data_r_max = "data_r_max"


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

        # Load the mesa data
        d = DP.load_from_pickle(settings.file_path_data1d)
        print("MESA data keys avaliable: ", d.keys())
        print("MESA data profiles avaliable: ", d[key_DataPrepTulips3D_prof_labels])

        # Create the geometry of the 3d pie slice
        ob = tulips3dGeometry.make_star_pie(\
            ob_name=settings.ob_name, \
            nr_R=d[key_DataPrepTulips3D_r_resolution], \
            # nr_R=settings.mesh_r_nr_steps, \
            nr_Th=settings.mesh_th_nr_steps, \
            verbose_timing=True)

        # Store all the dict data onto the Blender object
        for i, (k, v) in enumerate(d.items()):
            ob[k] = v

        # ob["testDataArray"] = d[key_DataPrepTulips3D_data_prof_t_r]

        # ob[key_ob_DataPrepTulips3D_data] = d

        # Create a dict as a custom property on the object to hold the arrays
        # ob[key_tulips_data] = {}
        ob[key_ob_active_data_label] = ob[key_DataPrepTulips3D_prof_labels][-1]
        ob[key_ob_active_time_index] = int(0)

        create_vert_col(ob)
        
        #update_profile(ob)


        return {'FINISHED'}

# ######################################################
# 
# ######################################################
def create_vert_col(ob):

    
    # _data = dict(ob[key_ob_DataPrepTulips3D_data])
    _profile_data = np.array(ob[key_DataPrepTulips3D_data_prof_t_r])
    _profile_data = _profile_data.reshape(\
        len(ob[key_DataPrepTulips3D_prof_labels]),\
        ob[key_DataPrepTulips3D_t_resolution],\
        ob[key_DataPrepTulips3D_r_resolution]\
        )
    
    _profile_labels = list(ob[key_DataPrepTulips3D_prof_labels])
    _profile_index = _profile_labels.index(ob[key_ob_active_data_label])


    for t in [0,250, 500, 750, 999]:#range(_profile_data.shape[1]):
        print("Making vert col: ", t, "/", _profile_data.shape[1])
        v = _profile_data[_profile_index, t, :]
        #index_prof = 
        #_data[key_DataPrepTulips3D_data_prof_t_r]

        #r, v = ob[key_tulips_data][ob[key_active_profile_key]][ob[active_time_index]]

        _data_r_max = np.array(ob[key_DataPrepTulips3D_data_r_max]).reshape(\
            len(ob[key_DataPrepTulips3D_prof_labels]),\
            ob[key_DataPrepTulips3D_t_resolution])
        r_max = _data_r_max[_profile_index, t]
        r = np.linspace(0., r_max, ob[key_DataPrepTulips3D_r_resolution])

        tulips3dGeometry.make_vertex_colors(\
                    np.array(r), np.array(v), ob.name, \
                    vertex_colors_name_base = "v_col_"+ob[key_ob_active_data_label]+"_"+str(t) \
                    )


def update_profile(ob):
    print()

# ######################################################
# HANDLERS
# ######################################################
def frame_change(scene):
    print("frame change")
    # for ob in bpy.data.objects:
    #     if key_tulips_data in list(ob.keys()):
    #         print("found key: ", key_tulips_data)

    #         ob[active_time_index] = scene.frame_current*ob.mesaAniStep
    #         ob.mesaProfileTime = ob[active_time_index]

    #         update_profile(ob)




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
    selected_profile = context.object.mesaProfileEnum
    selected = context.selected_objects
    if len(selected) == 1:
        ob = selected[0]
        if  selected_profile != ob[key_active_profile_key]:
            ob[key_active_profile_key] = selected_profile
            update_profile(ob)
        print("mesaDataProfEnum_update: STILL NEED TO USE TIME INDEX!!")

def mesaDataProfTime_update(scene, context):
    selected_time_index = context.object.mesaProfileTime
    selected = context.selected_objects
    if len(selected) == 1:
        ob = selected[0]
        if  selected_time_index != ob[active_time_index]:
            if selected_time_index <= len(ob[key_tulips_data][ob[key_active_profile_key]]):
                ob[active_time_index] = selected_time_index
            else:
                ob[active_time_index] = len(ob[key_tulips_data][ob[key_active_profile_key]])-1
                context.object.mesaProfileTime = ob[active_time_index]
            update_profile(ob)
    print("Time Update")



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
    bl_label = "Tulips3D Sidebar"
    bl_idname = "SIDEBAR_PT_tulips3d_panel"
    # bl_space_type = "PROPERTIES"
    # bl_region_type = "WINDOW"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tulips3D"
    # bl_context = "scene"          # appears under the Scene tab

    def draw(self, context):
        layout = self.layout
        # settings = context.scene.Tulips3DSettingsUI_sidebar

        col = layout.column()
        if len(bpy.context.selected_objects) > 0:
            ob = bpy.context.selected_objects[0]
            col.label(text = "Object: "+str(ob.name))
        else:
            col.label(text = "Object: ")
        # col.label(text = "Active profile: "+ob[key_active_profile_key])

        # col.prop(settings, "ob_name")
        # col.prop(settings, "mesaDataProfEnum")
        col.separator(factor=1.0, type='LINE')
        col.label(text = "MESA Profile: ")
        col.prop(context.object, "mesaProfileEnum")

        col.separator(factor=1.0, type='LINE')
        col.label(text = "MESA time index: ")
        col.prop(context.object, "mesaProfileTime")
        col.label(text = "Animation index step/frame: ")
        col.prop(context.object, "mesaAniStep")
        
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

    bpy.types.Object.mesaProfileTime = bpy.props.IntProperty(name="", step=1, default=0, min=0, description="int time index",\
        update=mesaDataProfTime_update)

    bpy.types.Object.mesaAniStep = bpy.props.IntProperty(name="", step=1, default=100, min=0, max=1500, description="time_index step per frame",\
        update=mesaDataProfTime_update)

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