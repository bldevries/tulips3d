

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

import sys
from time import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LogNorm
from scipy.interpolate import interp1d
from . import blackbody

import DataPrepTulips3D as DP
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


# ######################################################
# OPERATOR: tulips3d_update_objects
# ######################################################
# This operator can be used from scripts. Handlers are not always properly
# called in scripts and during rendering. So calling this makes sure
# all objects have the proper data on them.
class tulips3d_update_objects(bpy.types.Operator):
    """Operator to add Tulips3D geometry"""
    bl_idname = "object.tulips3d_update"
    bl_label = "Update Tulips3D Object(s)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("Update!", context)
        for ob in context.scene.objects:
            if "pie_type" in ob.keys():
                if ob["pie_type"] == "empty":
                    # print(f"Updating {ob.name}, done from {tulips3d_update_objects}")
                    # print(f"{ob.mesaProfileTime=}, {ob[key_ob_active_time_index]=}")
                    # update_profile(ob)
                    bpy.ops.object.select_all(action='DESELECT')
                    bpy.context.view_layer.objects.active = ob
                    ob.select_set(True)
                    ob.mesaProfileTime = ob.mesaProfileTime
                    ob[key_ob_active_time_index] = ob.mesaProfileTime

                if ob["pie_type"] == "master":
                    ob.select_set(True)
                    ob.starOpeningFactor = ob.starOpeningFactor
                    # print(f"MASTER {ob.starOpeningFactor=}")
            # print()
        return {'FINISHED'}

        # print("Tulips3d: Name of pie to add already exists. Doing nothing.")
        # return {'CANCELLED'}


# ######################################################
# OPERATOR tulips3d_add_all_pies
# ######################################################
# Adds all the pie parts with different data to form a 
# full star
class tulips3d_add_all_pies(bpy.types.Operator):
    """Operator to add Tulips3D geometry"""
    bl_idname = "object.tulips3d_add_all_pies"
    bl_label = "Create Tulips3D star with all data"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # We pull the current settings from 
        # context.scene.simple_geo_settings.
        settings = context.scene.Tulips3DSettingsUI 

        # context.scene['rendering_on'] = False

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

            d[key_DataPrepTulips3D_nr_theta_points] = settings.mesh_th_nr_steps+1

            list_of_objects = []
            list_of_profile_labels = ["Chem", "en", "mass", "logT", "logRho"]
            phi_step = 2*np.pi/len(list_of_profile_labels)

            for i, profile_label in enumerate(list_of_profile_labels):# enumerate(d[key_DataPrepTulips3D_prof_labels]+ ["Chem"]):
                phi_start = i*phi_step
                phi_end = (i+1)*phi_step
                
                print(f"Making PIE: {profile_label=} {phi_start=} {phi_end=}")

                ob = tulips3dGeometry.make_star_pie(\
                    ob_name=settings.ob_name+"_"+profile_label, \
                    R = BLENDER_STAR_SCALE,\
                    nr_R=d[key_DataPrepTulips3D_r_resolution], \
                    # nr_R=settings.mesh_r_nr_steps, \
                    nr_Th=settings.mesh_th_nr_steps, \
                    phi_start = phi_start,\
                    phi_step = phi_step,\
                    texture_path = settings.file_path_texture_star,\
                    verbose_timing=False)

                list_of_objects.append(ob)

                print("Object made")

                ob.select_set(True)


                # for ob in ob_empty.children:
                    # if ob["pie_type"] == "pie":
                for i, (k, v) in enumerate(d.items()):
                    ob[k] = v

                # Storing cummulative chem profiles
                _chem_data = np.array(ob[key_DataPrepTulips3D_data_chem_t_r])
                _chem_data = _chem_data.reshape(\
                    len(ob[key_DataPrepTulips3D_chem_elem_labels]),\
                    ob[key_DataPrepTulips3D_t_resolution],\
                    ob[key_DataPrepTulips3D_r_resolution]\
                    )
                
                
                # We will sum away the different chemical profile labels. So we need an array that has indices 
                # abundances_cummulative[chem.prof., time index, radial index].
                abundances_cummulative = np.zeros(_chem_data.shape)#(_chem_data.shape[1], _chem_data.shape[2]))
                # We need to know the number of theta indices
                nr_Th = ob[key_DataPrepTulips3D_nr_theta_points]
                # Iterate over the time indices
                for t in range(_chem_data.shape[1]):
                    for r in range(_chem_data.shape[2]):
                        abun = _chem_data[:, t, r] * nr_Th # The abundances at t, r scaled by the nr of theta points
                        # abundances = np.array([i for i in v[:, r_index]])*nr_Th
                        # abundances = v*nr_Th # We multiply with nr_Th since it will be in ratio to the theta indices
                        abundances_cummulative[:, t, r] = np.array([np.sum(abun[0:i+1]) for i in range(len(abun))]) 

                        # abundances_cummulative[t, :] = np.array([
                        #     np.array([np.sum(abundances[0:i+1, r_index]) 
                        #         for i in range(len(abundances[:, r_index]))]) 
                        #         for r_index in range(len(abundances[0, :]))])
                    
                ob[key_ob_cumm_abun_label] = abundances_cummulative

                print(f"Pre-calculated the chem. profiles. {abundances_cummulative.shape=}, {_chem_data.shape=}")
                print("Data stored on object")

                ob.select_set(True)

                # Create a dict as a custom property on the object to hold the arrays
                ob[key_ob_active_data_label] = profile_label# ob[key_DataPrepTulips3D_prof_labels][0]
                ob[key_ob_active_time_index] = int(0)

                update_profile(ob)#, verbose=True)
            
            # Add all the objects to one empty
            bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.object.empty_add(type="PLAIN_AXES")
            master_empty = bpy.context.active_object
            master_empty.name = settings.ob_name
            master_empty["pie_type"] = "master"
            master_empty.select_set(True)
            for ob in list_of_objects:
                ob.select_set(True)
            bpy.context.view_layer.objects.active = master_empty
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
            bpy.ops.object.select_all(action='DESELECT')


            print("Profile updated")

            return {'FINISHED'}

        print("Tulips3d: Name of pie to add already exists. Doing nothing.")
        return {'CANCELLED'}



# ######################################################
# OPERATOR OBJECT_OT_add_tulips3d_geo
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

            # Store the number of theta points used to create the object
            d[key_DataPrepTulips3D_nr_theta_points] = settings.mesh_th_nr_steps+1

            ob = tulips3dGeometry.make_star_pie(\
                ob_name=settings.ob_name, \
                R = BLENDER_STAR_SCALE,\
                nr_R=d[key_DataPrepTulips3D_r_resolution], \
                # nr_R=settings.mesh_r_nr_steps, \
                nr_Th=settings.mesh_th_nr_steps, \
                phi_start = settings.phi_start_pie/360. * 2*np.pi , \
                phi_step = 2*np.pi/len(d[key_DataPrepTulips3D_prof_labels]),\
                texture_path = settings.file_path_texture_star,\
                verbose_timing=False)

            print("Object made")

            ob.select_set(True)


            # for ob in ob_empty.children:
            for i, (k, v) in enumerate(d.items()):
                ob[k] = v

            # Storing cummulative chem profiles
            _chem_data = np.array(ob[key_DataPrepTulips3D_data_chem_t_r])
            _chem_data = _chem_data.reshape(\
                len(ob[key_DataPrepTulips3D_chem_elem_labels]),\
                ob[key_DataPrepTulips3D_t_resolution],\
                ob[key_DataPrepTulips3D_r_resolution]\
                )
            
            
            # We will sum away the different chemical profile labels. So we need an array that has indices 
            # abundances_cummulative[chem.prof., time index, radial index].
            abundances_cummulative = np.zeros(_chem_data.shape)#(_chem_data.shape[1], _chem_data.shape[2]))
            # We need to know the number of theta indices
            nr_Th = ob[key_DataPrepTulips3D_nr_theta_points]
            # Iterate over the time indices
            for t in range(_chem_data.shape[1]):
                for r in range(_chem_data.shape[2]):
                    abun = _chem_data[:, t, r] * nr_Th # The abundances at t, r scaled by the nr of theta points
                    abundances_cummulative[:, t, r] = np.array([np.sum(abun[0:i+1]) for i in range(len(abun))]) 
                
            ob[key_ob_cumm_abun_label] = abundances_cummulative

            print(f"Pre-calculated the chem. profiles. {abundances_cummulative.shape=}, {_chem_data.shape=}")
            print("Data stored on object")

            # Create a dict as a custom property on the object to hold the arrays
            ob[key_ob_active_data_label] = ob[key_DataPrepTulips3D_prof_labels][0]
            ob[key_ob_active_time_index] = int(0)

            update_profile(ob)#, verbose=True)
            
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
        print("  make_vertex_colors_surface")
        tulips3dGeometry.make_vertex_colors_surface(outer_sph, eff_temp_color, vertex_colors_name_base="test_surface_colors")

        # Update the pie slices with the data and rescale
        for pie_ob in pie_objects:
            if empty[key_ob_active_data_label] == "Chem":
                
                v = np.array(empty[key_ob_cumm_abun_label])
                v = v.reshape(\
                    len(empty[key_DataPrepTulips3D_chem_elem_labels]),\
                    empty[key_DataPrepTulips3D_t_resolution],\
                    empty[key_DataPrepTulips3D_r_resolution]\
                    )
                v = v[:, empty[key_ob_active_time_index], :]

                print("  make_chem_vertex_colors")
                tulips3dGeometry.make_chem_vertex_colors(\
                            np.array(r), np.array(v), pie_ob, labels=empty[key_DataPrepTulips3D_chem_elem_labels], nr_Th=empty[key_DataPrepTulips3D_nr_theta_points],\
                            vertex_colors_name_base = "v_col_active", \
                            verbose=False\
                            )
            else:
                # Get the data values corresponding to the current profile and time index
                v = _profile_data[_profile_index, empty[key_ob_active_time_index], :]
                print("  make_vertex_colors")
                tulips3dGeometry.make_vertex_colors(\
                            np.array(r), np.array(v), pie_ob, \
                            vertex_colors_name_base = "v_col_active", \
                            verbose=False\
                            )


            r_max_0 = _data_r_max[_profile_index, 0]

            empty.scale = [1.*r_max/r_max_0 for i in range(3)]
    print("** Done profile for ", ob.name)

# Global flag to indicate a pending update
_pending_update = False

def frame_change_safe(scene):
    """
    Called every frame. 
    It syncs the property but DOES NOT modify the mesh yet.
    """
    global _pending_update
    
    # Sync the property from the scene/object if needed
    # (Your existing logic to sync mesaProfileTime)
    for ob in scene.objects:
        if "pie_type" in ob.keys():
            if "master" in ob["pie_type"]:
                ob.select_set(True)
                ob.starOpeningFactor = ob.starOpeningFactor


        if key_ob_active_time_index in list(ob.keys()):
            # If the UI property changed, update the internal key
            if ob.mesaProfileTime != ob[key_ob_active_time_index]:
                ob[key_ob_active_time_index] = ob.mesaProfileTime
                _pending_update = True # Mark that we need an update
            
            # If the frame changed (and we are animating), update the time index
            # Note: You might need logic here to increment mesaProfileTime based on frame
            # For now, assuming mesaProfileTime is driven by keyframes or manual input
            
    # If we marked an update, schedule it via timer
    if _pending_update:
        # Register the timer if not already registered
        # if not hasattr(frame_change_safe, '_timer_registered'):
        bpy.app.timers.register(deferred_update)
        frame_change_safe._timer_registered = True
        # else:
            # frame_change_safe._timer_registered = True
        # print(f"frange change save ... {frame_change_safe._timer_registered=}")


def deferred_update():
    """
    Runs repeatedly until it's safe to update the mesh.
    Returns 0.1 if we need to wait, None if done.
    """
    global _pending_update
    

    print(f"deferred_update {_pending_update=}")

    # Check if rendering is happening
    # In Blender 4.5, is_rendering might be gone, so we use a try/except or check context
    is_rendering = False
    try:
        print(f"deferred_update try")

        # Try the standard way first
        if hasattr(bpy.context.scene.render, 'is_rendering'):
            is_rendering = bpy.context.scene.render.is_rendering
        # Fallback: Check if we are in a render context (less reliable but works sometimes)
        elif hasattr(bpy.context, 'scene') and bpy.context.scene.render:
             # If we are in a render job, the context might be different
             # But usually, if is_rendering is gone, we assume it's unsafe to modify mesh during render
             # A safer bet is to check if the render job is active in the job queue
             pass 
    except:
        print(f"deferred_update except")

        pass

    # If we are NOT rendering, it's safe to update
    if not is_rendering:
        print(f"deferred_update if not is_rendering")

        # Perform the heavy lifting
        for ob in bpy.context.scene.objects:
            if key_ob_active_time_index in list(ob.keys()):
                # Only update if the time index actually changed
                # (You might want to check if the value changed since last update)
                # For now, we just run update_profile if flagged
                if _pending_update:
                    # print(f"Updating profile for {ob.name} at time {ob[key_ob_active_time_index]}")
                    update_profile(ob)
        
        _pending_update = False # Reset flag
        return None # Stop the timer
    else:
        print(f"deferred_update return 0.1")

        # Still rendering, wait 0.1 seconds and check again
        return 0.5

# def frame_change(scene):
#     if not bpy.context.scene.render.is_rendering:
#     # if 'rendering_on' in scene:
#         # print(f"==> frame_change, {scene['rendering_on']=}")
#         # if not scene['rendering_on']:
#         print("frame change", scene)
#         for ob in scene.objects: #bpy.data.objects:
#             if key_ob_active_time_index in list(ob.keys()):
#                 if ob.mesaProfileTime != ob[key_ob_active_time_index]:
#                     ob[key_ob_active_time_index] = ob.mesaProfileTime
#                     # print("NOT THE SAME!!", ob.mesaProfileTime, ob[key_ob_active_time_index])

#                 update_profile(ob)



def render_init_handler(scene):
    # scene['rendering_on'] = True
    print(f"==> ANIMATION STARTING <==", scene.frame_current)
    scene.frame_set(scene.frame_start)
    frame_change_safe(scene)
    # print(scene.frame_current)

def render_stopped_handler(scene):
    # scene['rendering_on'] = False
    print(f"==> ANIMATION STOPPED <==", scene.frame_current)

def pre_render(scene):
    print(f"  ** FRAME STARTING", scene.frame_current)
    bpy.ops.object.tulips3d_update()
    # if bpy.context.scene.render.is_rendering:
    #     for ob in scene.objects: #bpy.data.objects:
    #         if key_ob_active_time_index in list(ob.keys()):
    #             if ob.mesaProfileTime != ob[key_ob_active_time_index]:
    #                 ob[key_ob_active_time_index] = ob.mesaProfileTime
    #                 # print("NOT THE SAME!!", ob.mesaProfileTime, ob[key_ob_active_time_index])

    #             update_profile(ob)



    # for ob in bpy.data.objects:
    #     if key_ob_active_time_index in list(ob.keys()):
    #         new_time_index = scene.frame_current*ob.mesaAniStep
    #         if new_time_index >= ob[key_DataPrepTulips3D_t_resolution]:
    #             new_time_index = ob[key_DataPrepTulips3D_t_resolution]-1

    #         ob[key_ob_active_time_index] = new_time_index
    #         ob.mesaProfileTime = ob[key_ob_active_time_index]

    #         update_profile(ob)

def post_render(scene):
    print(f"  ** FRAME POST", scene.frame_current)


def write_render(scene):
    print(f"  ** FRAME WRITE", scene.frame_current)




# This is called when the user selects a blender object 
# and it updates which enum options are available in the
# sidebar
def mesaDataProfEnum_callback(scene, context):
    # print("** mesaDataProfEnum_callback")
    # print("SELECTING!!!!!!", bpy.context.selected_objects)
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
    # print("** mesaDataProfEnum_update ")
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
    # print("** mesaDataProfTime_update", context)#.selected_objects)
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



def open_star(ob, r=0.1):
    if not 'pie_type' in ob.keys():
        return None
    if not 'master' in ob['pie_type']:
        return None
    
    for empty_child in ob.children:
        if not 'empty' in empty_child['pie_type']:
            return None
        
        rot_ob_z = empty_child.rotation_euler[2] + 1/2 * 2*np.pi/5.
        dx = -np.sin(rot_ob_z)
        dy = np.cos(rot_ob_z)
        empty_child.location = (r*dx, r*dy, 0.)



def starOpeningFactor_update(scene, context):
    # print("starOpeningFactor_update", f"{context=}", context.keys)
    opening = context.object.starOpeningFactor
    selected = context.selected_objects
    open_star(selected[0], r=opening)


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

        col.separator()
        col.operator("object.tulips3d_add_all_pies", icon='MESH_CUBE')



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
        # print("==> SIDEBAR_PT_tulips3d_panel ")
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
                if (context.object['pie_type'] != "empty") and (context.object['pie_type'] != "master"):
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
                
                if context.object['pie_type'] == "master":
                    col.separator(factor=1.0, type='LINE')
                    col.label(text = "Opening factor: ")
                    col.prop(ob, "starOpeningFactor")

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
    tulips3d_add_all_pies,
    tulips3d_update_objects,
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

    bpy.types.Object.starOpeningFactor = bpy.props.FloatProperty(name="", default=0, min=0, max=15, description="",\
        update=starOpeningFactor_update)


    # Attach an empty CollectionProperty to every Object
    bpy.types.Object.stellarProperties = CollectionProperty(
        type=StellarEvolutionProperties,
        name="Stellar evolution data",
        description="Stellar evolution properties (like t and R) as function of time"
    )

    # bpy.app.handlers.frame_change_pre.append(frame_change)
    # bpy.app.handlers.frame_change_post.append(frame_change)
    bpy.app.handlers.frame_change_pre.append(frame_change_safe)
    
    # bpy.app.handlers.render_init.append(render_init_handler)
    # bpy.app.handlers.render_complete.append(render_stopped_handler)
    # bpy.app.handlers.render_cancel.append(render_stopped_handler)

    

    # # For testing
    bpy.app.handlers.render_pre.append(pre_render)
    # bpy.app.handlers.render_post.append(post_render)
    # bpy.app.handlers.render_write.append(write_render)

def unregister():
    # Remove the property first
    if hasattr(bpy.types.Scene, "Tulips3DSettingsUI"):
        del bpy.types.Scene.Tulips3DSettingsUI
        
    # del bpy.types.Scene.Tulips3DSettingsUI
    # del bpy.types.Scene.Tulips3DSettingsUI_sidebar
    if hasattr(bpy.types.Object, "stellarProperties"):
        del bpy.types.Object.stellarProperties

    # for cls in reversed(classes):
    #     bpy.utils.unregister_class(cls)
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            # This happens if the class was never registered or already removed
            pass 
    try:
        # handler_list.remove(handler_func)
        bpy.app.handlers.frame_change_pre.remove(frame_change_safe)
        print(f"Handler frame_change_safe removed successfully.")
    except ValueError:
        # This error means the handler was not in the list
        print(f"Handler frame_change_safe was not found in the list (already removed).")
    except AttributeError:
        # This happens if the handler_func itself doesn't exist anymore
        print(f"Handler function frame_change_safe does not exist.")

    # try:
    #     # handler_list.remove(handler_func)
    #     bpy.app.handlers.render_pre.remove(pre_render)
    #     print(f"Handler pre_render removed successfully.")
    # except ValueError:
    #     # This error means the handler was not in the list
    #     print(f"Handler pre_render was not found in the list (already removed).")
    # except AttributeError:
    #     # This happens if the handler_func itself doesn't exist anymore
    #     print(f"Handler function pre_render does not exist.")

    # bpy.app.handlers.frame_change_pre.remove(frame_change)
    # bpy.app.handlers.frame_change_post.remove(frame_change)
    

    # bpy.app.handlers.render_init.remove(render_init_handler)
    # bpy.app.handlers.render_complete.remove(render_stopped_handler)
    # bpy.app.handlers.render_cancel.remove(render_stopped_handler)

    # # Testing
    
    # bpy.app.handlers.render_post.remove(post_render)
    # bpy.app.handlers.render_write.remove(write_render)

# if __name__ == "__main__":
#     register()