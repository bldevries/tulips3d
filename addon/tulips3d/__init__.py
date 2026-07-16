

if "bpy" in locals():
    import importlib
    importlib.reload(colormodels)
    importlib.reload(generate_nodes)
    importlib.reload(tulips3dGeometry)
    importlib.reload(tulips3dGeometrySimple)
else:
    from . import colormodels
    # from . import tulips3dData
    from . import tulips3dGeometry
    from . import tulips3dGeometrySimple
    from . import generate_nodes

import bpy
from bpy.props import (
    FloatProperty,
    StringProperty,
    IntProperty,
    EnumProperty,
    CollectionProperty
)

import sys, os
from time import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LogNorm
from scipy.interpolate import interp1d
from . import blackbody
import pickle

# import DataPrepTulips3D as DP
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

key_ob_cumm_abun_label = "abundances_cummulative"
key_DataPrepTulips3D_nr_theta_points = "nr_Th"

# The data_array (given by DP.load_from_pickle) will contain 
# the "data_prof_t_r" key. It contains the MESA data in the 
# resolution (prof_labels, t_resolution, r_resolution)
key_DataPrepTulips3D_data_prof_t_r = "data_prof_t_r"
key_DataPrepTulips3D_data_chem_t_r = "data_chem_t_r"
key_DataPrepTulips3D_data_t = "data_t"
key_DataPrepTulips3D_data_t_Teff = "logTeff"

key_DataPrepTulips3D_data_r_max = "data_r_max"

key_DataPrepTulips3D_dir_structure = "dir_structure"
key_DataPrepTulips3D_texture_dir = "texture_dir"
key_DataPrepTulips3D_data_t_r_filename = "dir_structure_data_t_r_filename"
key_DataPrepTulips3D_chem_abun_filename = "dir_structure_chem_abun_filename"
key_DataPrepTulips3D_data_t_filename_and_max = "dir_structure_data_t_filename_and_max"

# ######################################################
#
# ######################################################
def load_from_pickle(filepath):
    '''Reads a dict from a pickle file'''
    dbfile = open(filepath, 'rb')    
    data_dict = pickle.load(dbfile)
    return data_dict


# ######################################################
# OPERATOR: READ DIR
# ######################################################
class tulips3d_read_dir(bpy.types.Operator):
    """Operator to add Tulips3D geometry"""
    bl_idname = "object.tulips3d_read_dir"
    bl_label = "Read in Tulips3D directory"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.Tulips3DSettingsUI 
        print(f"Reading in Tulips3D dir {settings.dir_path_data1d}")
        directory = settings.dir_path_data1d
        d = load_from_pickle(os.path.join(directory, "MESA_data_dict.pkl"))
            # for ob in ob_empty.children:

        ob = tulips3dGeometrySimple.make_star_pie(\
            ob_name=settings.ob_name,\
            R=BLENDER_STAR_SCALE, \
            nr_R = d[key_DataPrepTulips3D_r_resolution], \
            nr_Th = settings.mesh_th_nr_steps, \
            texture_path="",\
            phi_start = 0.0, phi_step=30.0/360*2*np.pi, verbose_timing=False,\
            )

        print()
        # print(d.)
        print()

        for i, (k, v) in enumerate(d.items()):
            print(i, k)
            ob[k] = v

        for sub_ob in ob.children:
            print()
            print(sub_ob.name)
            print(d[key_DataPrepTulips3D_dir_structure][key_DataPrepTulips3D_data_t_filename_and_max].keys())
            text_dir = d[key_DataPrepTulips3D_dir_structure][key_DataPrepTulips3D_texture_dir]
            text_path = os.path.join(directory, text_dir)
            Rmax_exr_filename = d[key_DataPrepTulips3D_dir_structure][key_DataPrepTulips3D_data_t_filename_and_max]["Rmax"]["filename"]
            Rmax_exr_path = os.path.join(text_path, Rmax_exr_filename)
            print(os.path.isfile(Rmax_exr_path), Rmax_exr_path)
            
            Teff_exr_filename = d[key_DataPrepTulips3D_dir_structure][key_DataPrepTulips3D_data_t_filename_and_max]["colored_logTeff"]["filename"]
            Teff_exr_path = os.path.join(text_path, Teff_exr_filename)
            print(os.path.isfile(Teff_exr_path), Teff_exr_path)

            profile_label = "chem"
            profile_path = get_profile_texture_path(d, directory, profile_label)

            star_radius_attr_name = "StarRadiusAttribute"
            Teff_attr_name = "TeffAttribute"
            if sub_ob["pie_type"] == "pie":
                generate_nodes.add_geo_nodes(sub_ob, \
                    radius_texture_path=Rmax_exr_path, teff_texture_path=Teff_exr_path,\
                    star_radius_attr_name=star_radius_attr_name, \
                    Teff_attr_name=Teff_attr_name)
                material_name = ob.name+"_"+sub_ob.name+"_mat"
                sub_ob.data.materials.append(
                    generate_nodes.create_material_data_t_r(material_name, data_texture_path=profile_path))
            elif sub_ob["pie_type"] == "outer_sph":
                generate_nodes.add_geo_nodes(sub_ob, \
                    radius_texture_path=Rmax_exr_path, teff_texture_path=Teff_exr_path,\
                    star_radius_attr_name=star_radius_attr_name, \
                    Teff_attr_name=Teff_attr_name)
                material_name = ob.name+"_"+sub_ob.name+"_Teff_mat"
                sub_ob.data.materials.append(
                    generate_nodes.create_material_Teff(material_name, color_attr_name=Teff_attr_name))
            
                # !!!! ! Teff coloring using  new create_material_data_t

        return {'FINISHED'}
    # return {'CANCELLED'}


def get_profile_texture_path(d, directory, profile_label):
    '''Retrieves the path to the texture containing the data for the profile label'''
    text_dir = d[key_DataPrepTulips3D_dir_structure][key_DataPrepTulips3D_texture_dir]
    text_path = os.path.join(directory, text_dir)
    if profile_label == "chem":
        profile_dir_name = "chem_abun_color"
        profile_path = os.path.join(text_path, profile_dir_name)
        profile_path = os.path.join(\
                        profile_path, \
                        d[key_DataPrepTulips3D_dir_structure][key_DataPrepTulips3D_chem_abun_filename].replace("#", "0"))
        print(os.path.isfile(profile_path), profile_path)

    else:
        profile_dir_name = profile_label
        profile_path = os.path.join(text_path, profile_dir_name)
        profile_path = os.path.join(\
                        profile_path, \
                        d[key_DataPrepTulips3D_dir_structure][key_DataPrepTulips3D_data_t_r_filename].replace("#", "0"))
        print(os.path.isfile(profile_path), profile_path)

    return profile_path

def get_prof_enum(scene, context):
    ''' Called when an object gets selected. Updated the dropdown menu for profile selection in the sidebar'''
    items = []
    if len(context.selected_objects) > 0:
        ob = context.selected_objects[0]
        print("Getting enum list", ob)

        if "pie_type" in ob.keys() and ob.parent:
            if ob['pie_type'] == "pie":
                for k in list(ob.parent[key_DataPrepTulips3D_prof_labels])+["chem"]:
                    items.append((k, k, ""))
    print("  ", items)
    return items

def update_profile(scene, context):
    selected_profile = context.object.mesaProfileEnum
    selected = context.selected_objects

    settings = context.scene.Tulips3DSettingsUI 
    directory = settings.dir_path_data1d

    if len(selected) > 0:
        ob = context.selected_objects[0]

        if ob["pie_type"] == "pie":
            print("Updating", ob.name)

            mat = ob.material_slots[0].material
            print("Mat name", mat.name)
            # if material_name in mat.name:
                # print("Mat naming: ", material_name, mat.name)
            print(mat)
            
            profile_path2 = get_profile_texture_path(ob.parent, directory, selected_profile)
            print("Update succes: ", generate_nodes.update_material(mat, profile_path2))

def mesaDataProfTime_update(scene, context):
    print("mesaDataProfTime_update not implemented yet")
    # print("** mesaDataProfTime_update", context)#.selected_objects)
    # selected_time_index = context.object.mesaProfileTime
    # selected = context.selected_objects
    
    # # print("mesaDataProfTime_update")

    # if len(selected) == 1:
    #     if selected[0]['pie_type'] == "empty":
    #         selected = selected[0]#.parent

    #         if selected_time_index != selected[key_ob_active_time_index]:
    #             if selected_time_index < selected[key_DataPrepTulips3D_t_resolution]:
    #                 selected[key_ob_active_time_index] = selected_time_index
    #                 #ob.mesaProfileTime = selected_time_index
    #             else:
    #                 selected[key_ob_active_time_index] = selected[key_DataPrepTulips3D_t_resolution]-1
    #                 # context.object.mesaProfileTime = ob[key_ob_active_time_index]
    #                 # Update only the property for the objects not selected
    #                 selected.mesaProfileTime = selected[key_DataPrepTulips3D_t_resolution]-1#ob[key_ob_active_time_index]

                # update_profile(selected)
    # print("Time Update")

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

    # file_path_data1d_default = '/Users/vries001/Dropbox/0_DATA_BEN/PHYSICS/PROJECTS/tulips3D/example_MESA_data/DataDictFormat/binary.pkl'
    dir_path_data1d : StringProperty(
        name="MESA data directory",
        description="MESA data directory",
        # default=file_path_data1d_default,
        subtype="DIR_PATH"
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

    mesh_th_nr_steps : IntProperty(
        name="Theta #steps mesh",
        description="",
        default=50,
        # min=3,
        # max=256,
    )


class VIEW3D_PT_tulips3d_read_dir_panel(bpy.types.Panel):
    """Panel placed in the Properties editor → Scene tab"""
    bl_label = "Tulips3D Load File"
    bl_idname = "VIEW3D_PT_tulips3d_read_dir_panel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"          # appears under the Scene tab

    def draw(self, context):
        layout = self.layout
        settings = context.scene.Tulips3DSettingsUI

        col = layout.column()
        col.prop(settings, "ob_name")
        col.prop(settings, "dir_path_data1d")

        col.separator()
        col.operator("object.tulips3d_read_dir", icon='MESH_CUBE')

class SIDEBAR_PT_tulips3d_panel(bpy.types.Panel):
    """ 3D viewport Sidebar panel """
    bl_label = "Tulips3D Sidebar"
    bl_idname = "SIDEBAR_PT_tulips3d_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tulips3D"

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        if len(bpy.context.selected_objects) > 0:
            ob = bpy.context.selected_objects[0]
            col.label(text = "Object: "+str(ob.name))
        else:
            col.label(text = "Object: ")

        if context.object:
            if 'pie_type' in context.object.keys():

                if context.object['pie_type'] == "pie":
                    col.separator(factor=1.0, type='LINE')
                    col.label(text = "MESA Profile: ")
                    col.prop(ob, "mesaProfileEnum")

                    col.separator(factor=1.0, type='LINE')
                    col.label(text = "MESA time index: ")
                    col.prop(ob, "mesaProfileTime")
                
                if context.object['pie_type'] == "master":
                    col.separator(factor=1.0, type='LINE')
                    col.label(text = "Opening factor: ")
                    col.prop(ob, "starOpeningFactor")

# ######################################################
# REGISTERING AND STUFF
# ######################################################
classes = (
    Tulips3DSettingsUI,
    tulips3d_read_dir,
    VIEW3D_PT_tulips3d_read_dir_panel,
    SIDEBAR_PT_tulips3d_panel,
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
        items=get_prof_enum,\
        update=update_profile)#mesaDataProfEnum_update)

    bpy.types.Object.mesaProfileTime = bpy.props.IntProperty(name="", step=1, default=0, min=0, description="int time index",\
        update=mesaDataProfTime_update)

    bpy.types.Object.mesaAniStep = bpy.props.IntProperty(name="", step=1, default=1, min=0, max=1500, description="time_index step per frame",\
        update=mesaDataProfTime_update)

def unregister():
    # Remove the property first
    if hasattr(bpy.types.Scene, "Tulips3DSettingsUI"):
        del bpy.types.Scene.Tulips3DSettingsUI

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            # This happens if the class was never registered or already removed
            pass 
