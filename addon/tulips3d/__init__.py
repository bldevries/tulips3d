

if "bpy" in locals():
    import importlib
    importlib.reload(colormodels)
    # importlib.reload(tulips3dData)
    importlib.reload(tulips3dGeometry)

else:
    from . import colormodels
    # from . import tulips3dData
    from . import tulips3dGeometry

from . import blackbody

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
    "version": (0, 0, 1.1),
    "blender": (4, 5, 0),          # <-- target version
    "location": "Properties > Scene",
    "description": "Adds a 3d visualisation of the output of the MESA stellar evolution code.",
    "category": "Object",
}

BLENDER_STAR_SCALE = 10.

# OBJECT KEYS TO TRACK
key_ob_DataPrepTulips3D_data = 'tulips_grid_data' # This holds the DataPrepTulips3D dict
key_ob_active_data_label = 'tulips_active_profile_key' # Label of the currently shown data 
key_ob_active_time_index = 'active_time_index' # Currently shown time index

key_blender_ob_data_dict = "MESA_data_dict"


# Keys of the dict coming from the DataPrepTulips3D
key_DataPrepTulips3D_prof_labels = "prof_labels"
key_DataPrepTulips3D_chem_elem_labels = "chem_elem_labels"
key_DataPrepTulips3D_r_resolution = "r_resolution"
key_DataPrepTulips3D_t_resolution = "t_resolution"

key_DataPrepTulips3D_nr_theta_points = "nr_Th"

# The data_array (given by DP.load_from_pickle) will contain 
# the "data_prof_t_r" key. It contains the MESA data in the 
# resolution (prof_labels, t_resolution, r_resolution)
key_DataPrepTulips3D_data_prof_t_r = "data_prof_t_r"
key_DataPrepTulips3D_data_chem_t_r = "data_chem_t_r"
key_DataPrepTulips3D_data_t = "data_t"
key_DataPrepTulips3D_data_t_Teff = "logTeff"

key_DataPrepTulips3D_data_r_max = "data_r_max"


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
        # We pull the current settings from 
        # context.scene.simple_geo_settings.
        settings = context.scene.Tulips3DSettingsUI 

        object_found = False
        for o in bpy.context.scene.objects:
            if o.name == settings.ob_name:
                object_found = True

        if not object_found:
            # Load the mesa data
            d = DP.load_from_pickle(settings.file_path_data1d)

            print("MESA data keys avaliable: ", d.keys())
            print("MESA data profiles avaliable: ", \
                d[key_DataPrepTulips3D_prof_labels])

            #d[key_DataPrepTulips3D_prof_labels].append("Chem")
            # Store the number of theta points used to create the object
            d[key_DataPrepTulips3D_nr_theta_points] = settings.mesh_th_nr_steps+1

            ob = tulips3dGeometry.make_star_pie(\
                ob_name=settings.ob_name, \
                R = BLENDER_STAR_SCALE,\
                nr_R=d[key_DataPrepTulips3D_r_resolution], \
                # nr_R=settings.mesh_r_nr_steps, \
                nr_Th=settings.mesh_th_nr_steps, \
                phi_start = settings.phi_start_pie/360. * 2*np.pi , \
                phi_end = 2*np.pi/len(d[key_DataPrepTulips3D_prof_labels]),\
                texture_path = settings.file_path_texture_star,\
                verbose_timing=False)

            print("Object made")

            ob.select_set(True)


            # for ob in ob_empty.children:
                # if ob["pie_type"] == "pie":
            for i, (k, v) in enumerate(d.items()):
                ob[k] = v

            print("Data stored on object")

            # Create a dict as a custom property on the object to hold the arrays
            ob[key_ob_active_data_label] = ob[key_DataPrepTulips3D_prof_labels][0]
            ob[key_ob_active_time_index] = int(0)

            # for child in ob.children:
            #     # if child["pie_type"] == "pie":
            #     child[key_ob_active_data_label] = ob[key_DataPrepTulips3D_prof_labels][0]
            #     child[key_ob_active_time_index] = int(0)

            print("Actives set")

            update_profile(ob)#, verbose=True)
            
            print("Profile updated")

            return {'FINISHED'}

        print("Tulips3d: Name of pie to add already exists. Doing nothing.")
        return {'CANCELLED'}




# ######################################################
# HANDLERS & CALLBACKS
# ######################################################

def update_profile(ob):
    """Updates the profile of ob"""
    print("** Updating profile for ", ob.name)
    pie_objects = []
    outer_sph = None
    if "pie_type" in ob.keys():
        if ob["pie_type"] == "empty":
            empty = ob
        else:
            empty = ob.parent

        for child in empty.children:
            if child["pie_type"] == "pie":
                pie_objects.append(child)
            elif child["pie_type"] == "outer_sph":
                outer_sph = child

        # Cast and reshape the data into a proper numpy array
        _profile_data = np.array(empty[key_DataPrepTulips3D_data_prof_t_r])
        _profile_data = _profile_data.reshape(\
            len(empty[key_DataPrepTulips3D_prof_labels]),\
            empty[key_DataPrepTulips3D_t_resolution],\
            empty[key_DataPrepTulips3D_r_resolution]\
            )

        _chem_data = np.array(empty[key_DataPrepTulips3D_data_chem_t_r])
        _chem_data = _chem_data.reshape(\
            len(empty[key_DataPrepTulips3D_chem_elem_labels]),\
            empty[key_DataPrepTulips3D_t_resolution],\
            empty[key_DataPrepTulips3D_r_resolution]\
            )

        # Get the profile labels as a list        
        _profile_labels = list(empty[key_DataPrepTulips3D_prof_labels])
        # Get the current profile label
        if empty[key_ob_active_data_label] == "Chem":   

            _profile_index = 0 # THIS IS TEMPORARY!!!!!
        else:
            _profile_index = _profile_labels.index(empty[key_ob_active_data_label])

       
        # Get the r_max data and cast/reshape into np array
        _data_r_max = np.array(empty[key_DataPrepTulips3D_data_r_max]).reshape(\
            len(empty[key_DataPrepTulips3D_prof_labels]),\
            empty[key_DataPrepTulips3D_t_resolution])
        # Get the r_max for the current time index
        r_max = _data_r_max[_profile_index, empty[key_ob_active_time_index]]
        # Generate an r array using the given resolution
        r = np.linspace(0., r_max, empty[key_DataPrepTulips3D_r_resolution])

        # Update the outer shell of the star
        # First get the data that only depens on time
        _profile_data_t = empty[key_DataPrepTulips3D_data_t]
        # Then fetch the logTeff data
        arrTeff = _profile_data_t[key_DataPrepTulips3D_data_t_Teff]
        logTeff = np.array(arrTeff)[empty[key_ob_active_time_index]]
        # And make a colour of the logTeff
        eff_temp_color = [i/255 for i in colormodels.irgb_from_xyz(blackbody.blackbody_color(10**logTeff))]
        # Add the alpha channel
        eff_temp_color = eff_temp_color + [1.]

        # Update the surface colors
        tulips3dGeometry.make_vertex_colors_surface(outer_sph, eff_temp_color, vertex_colors_name_base="test_surface_colors")

        # Update the pie slices with the data and rescale
        for pie_ob in pie_objects:
            if empty[key_ob_active_data_label] == "Chem":
                v = _chem_data[:, empty[key_ob_active_time_index], :]
                tulips3dGeometry.make_chem_vertex_colors(\
                            np.array(r), np.array(v), pie_ob, labels=empty[key_DataPrepTulips3D_chem_elem_labels], nr_Th=empty[key_DataPrepTulips3D_nr_theta_points],\
                            vertex_colors_name_base = "v_col_active", \
                            verbose=False\
                            )
            else:
                # Get the data values corresponding to the current profile and time index
                v = _profile_data[_profile_index, empty[key_ob_active_time_index], :]

                tulips3dGeometry.make_vertex_colors(\
                            np.array(r), np.array(v), pie_ob, \
                            vertex_colors_name_base = "v_col_active", \
                            verbose=False\
                            )


            r_max_0 = _data_r_max[_profile_index, 0]

            empty.scale = [1.*r_max/r_max_0 for i in range(3)]



def frame_change(scene):
    print("frame change")
    for ob in bpy.data.objects:
        if key_ob_active_time_index in list(ob.keys()):
            if ob.mesaProfileTime != ob[key_ob_active_time_index]:
                ob[key_ob_active_time_index] = ob.mesaProfileTime
                # print("NOT THE SAME!!", ob.mesaProfileTime, ob[key_ob_active_time_index])

            update_profile(ob)

    # for ob in bpy.data.objects:
    #     if key_ob_active_time_index in list(ob.keys()):
    #         new_time_index = scene.frame_current*ob.mesaAniStep
    #         if new_time_index >= ob[key_DataPrepTulips3D_t_resolution]:
    #             new_time_index = ob[key_DataPrepTulips3D_t_resolution]-1

    #         ob[key_ob_active_time_index] = new_time_index
    #         ob.mesaProfileTime = ob[key_ob_active_time_index]

    #         update_profile(ob)




# This is called when the user selects a blender object 
# and it updates which enum options are available in the
# sidebar
def mesaDataProfEnum_callback(scene, context):
    print("** mesaDataProfEnum_callback")
    # print("SELECTING!!!!!!", bpy.context.selected_objects)
        # context.scene.Tulips3DSettingsUI_sidebar.mesaDataProfEnum, \
        # type(context.scene.Tulips3DSettingsUI_sidebar.mesaDataProfEnum))
    items = []
    # get selection
    selection = bpy.context.selected_objects
    
    # Check if it has a parent: bpy.context.selected_objects[0].parent == None
    # The data can also be stored on the parent

    # print("mesaDataProfEnum_callback", selection)
    if len(selection) == 1:
        # print("  mesaDataProfEnum_callback", "selection==1")
        ob = bpy.context.selected_objects[0]
        # Check if the object has mesa profile data attached
        # if key_DataPrepTulips3D_prof_labels in ob.keys():
        if "pie_type" in ob.keys():
            if ob['pie_type'] != "empty":
                ob = ob.parent
            for k in list(ob[key_DataPrepTulips3D_prof_labels])+["Chem"]:
                items.append((k, k, ""))
        

        # Set the enum to the current active data
        # context.scene.Tulips3DSettingsUI_sidebar.mesaDataProfEnum = ob[key_active_profile_key]
    return items

# This is called when the user selects a mesa profile in the sidebar
# and this should this update the geometry
def mesaDataProfEnum_update(scene, context):
    print("** mesaDataProfEnum_update ")
    selected_profile = context.object.mesaProfileEnum
    selected = context.selected_objects
    # print("mesaDataProfEnum_update", selected)
    if len(selected) == 1:
        # print("  mesaDataProfEnum_update", len(selected))
        ob = selected[0]

        if "pie_type" in ob.keys():
            if ob['pie_type'] != "empty":
                ob = ob.parent

            if  selected_profile != ob[key_ob_active_data_label]:
                ob[key_ob_active_data_label] = selected_profile
                #ob.mesaProfileEnum = selected_profile
                # for child in ob.children:
                #     # if child["pie_type"] == "pie":
                #     child[key_ob_active_data_label] = selected_profile
                #     child.mesaProfileEnum = selected_profile
                update_profile(ob)
            # else:
                # print("  mesaDataProfEnum_update", "NOT UPDATING LABEL")

def mesaDataProfTime_update(scene, context):
    print("** mesaDataProfTime_update", context.selected_objects)
    selected_time_index = context.object.mesaProfileTime
    selected = context.selected_objects
    
    # print("mesaDataProfTime_update")

    if len(selected) == 1:
        if selected[0]['pie_type'] == "empty":
            selected = selected[0]#.parent

            if selected_time_index != selected[key_ob_active_time_index]:
                if selected_time_index < selected[key_DataPrepTulips3D_t_resolution]:
                    selected[key_ob_active_time_index] = selected_time_index
                    #ob.mesaProfileTime = selected_time_index
                else:
                    selected[key_ob_active_time_index] = selected[key_DataPrepTulips3D_t_resolution]-1
                    # context.object.mesaProfileTime = ob[key_ob_active_time_index]
                    # Update only the property for the objects not selected
                    selected.mesaProfileTime = selected[key_DataPrepTulips3D_t_resolution]-1#ob[key_ob_active_time_index]

                update_profile(selected)
    # print("Time Update")


# def mesaDataProfTime_update(scene, context):
#     selected_time_index = context.object.mesaProfileTime
#     selected = context.selected_objects
    
#     # print("mesaDataProfTime_update")

#     if len(selected) == 1:
#         ob = selected[0]
#         if  selected_time_index != ob[key_ob_active_time_index]:
            
#             if selected_time_index < ob[key_DataPrepTulips3D_t_resolution]:
#                 ob[key_ob_active_time_index] = selected_time_index
#             else:
#                 ob[key_ob_active_time_index] = ob[key_DataPrepTulips3D_t_resolution]-1
#                 context.object.mesaProfileTime = ob[key_ob_active_time_index]


#             update_profile(ob)
#     # print("Time Update")


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
    
    file_path_data1d_default = '/Users/vries001/Dropbox/0_DATA_BEN/PHYSICS/PROJECTS/tulips3D/example_MESA_data/DataDictFormat/binary.pkl'
    file_path_data1d : StringProperty(
        name="MESA data in Data1D format path",
        description="MESA data in Data1D format path",
        default=file_path_data1d_default,
        subtype="FILE_PATH"
    )

    file_path_texture_star_default = '/Users/vries001/Dropbox/0_DATA_BEN/PHYSICS/PROJECTS/tulips3D/example_MESA_data/DataDictFormat/binary.pkl'
    file_path_texture_star : StringProperty(
        name="Star texture",
        description="Texture to apply to the outside of the star",
        default=file_path_texture_star_default,
        subtype="FILE_PATH"
    )

    phi_start_pie : FloatProperty(
        name="Phi start",
        description="Phi angle at which to start the pie",
        default=0.0,
        # min=3,
        # max=256,
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

    # time_index_step : IntProperty(
    #     name="time_index_step",
    #     description="Time index step size for animation",
    #     default=1000,
    #     # min=3,
    #     # max=256,
    # )

    # mesh_r_nr_steps : IntProperty(
    #     name="Radial #steps mesh",
    #     description="",
    #     default=50,
    #     # min=3,
    #     # max=256,
    # )

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
        # col.prop(settings, "time_index_step")
        # col.prop(settings, "mesh_r_nr_steps")
        col.prop(settings, "mesh_th_nr_steps")
        col.prop(settings, "phi_start_pie")
        col.prop(settings, "file_path_texture_star")
        # col.prop(settings, "shape")
        # col.prop(settings, "size")
        # col.prop(settings, "segments")

        col.separator()
        col.operator("object.tulips3d", icon='MESH_CUBE')



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
        print("==> SIDEBAR_PT_tulips3d_panel ")
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

        if context.object:
            if 'pie_type' in context.object.keys():
                if context.object['pie_type'] != "empty":
                    ob = context.object.parent
                else:
                    ob = context.object

            if 'pie_type' in context.object.keys():
                if context.object['pie_type'] == "empty":
                    col.separator(factor=1.0, type='LINE')
                    col.label(text = "MESA Profile: ")
                    col.prop(ob, "mesaProfileEnum")

                    col.separator(factor=1.0, type='LINE')
                    col.label(text = "MESA time index: ")
                    col.prop(ob, "mesaProfileTime")
        # col.label(text = "Animation index step/frame: ")
        # col.prop(context.object, "mesaAniStep")
        
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
        default = 0,\
        items=mesaDataProfEnum_callback,\
        update=mesaDataProfEnum_update)

    bpy.types.Object.mesaProfileTime = bpy.props.IntProperty(name="", step=1, default=0, min=0, description="int time index",\
        update=mesaDataProfTime_update)

    bpy.types.Object.mesaAniStep = bpy.props.IntProperty(name="", step=1, default=1, min=0, max=1500, description="time_index step per frame",\
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