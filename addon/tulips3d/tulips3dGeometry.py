
if "bpy" in locals():
    import importlib
    importlib.reload(colormodels)
else:
    from . import colormodels

import bpy
import bmesh

import numpy as np
import math
import sys
from time import time
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, to_rgb
from matplotlib.colors import Normalize, LogNorm
from scipy.interpolate import interp1d

# For cmaps:
# import cmasher as cmr
CMAP_BASE = ListedColormap([ "#40C4FF",     # dark blue - h1
                             "#64B5F6",     # lighter dark blue - he3
                             "#2962FF",     # light blue - he4
                             "#C6FF00",     # lime - c12
                             "#18FFFF",     # cyan - n14
                             "#00C853",     # dark green - o16
                             "#69F0AE",     # light green - ne20
                             "#8D6E63",     # light brown - mg24
                             "#5D4037",     # brown - si28
                             "#BDBDBD",     # grey - s32
                             "#2f0596",     # ar36
                             "#4903a0",     # ca40
                             "#6100a7",     # ti47
                             "#8707a6",     # cr48
                             "#ba3388",     # cr56
                             "#de6164",     # fe52
                             "#e66c5c",     # fe54
                             "#ed7953",     # fe56
                             "#feb72d",     # ni56
                             ])

CMAP_RGBA = [(0.25098039215686274, 0.7686274509803922, 1.0, 1.0), (0.39215686274509803, 0.7098039215686275, 0.9647058823529412, 1.0), (0.1607843137254902, 0.3843137254901961, 1.0, 1.0), (0.7764705882352941, 1.0, 0.0, 1.0), (0.09411764705882353, 1.0, 1.0, 1.0), (0.0, 0.7843137254901961, 0.3254901960784314, 1.0), (0.4117647058823529, 0.9411764705882353, 0.6823529411764706, 1.0), (0.5529411764705883, 0.43137254901960786, 0.38823529411764707, 1.0), (0.36470588235294116, 0.25098039215686274, 0.21568627450980393, 1.0), (0.7411764705882353, 0.7411764705882353, 0.7411764705882353, 1.0), (0.1843137254901961, 0.0196078431372549, 0.5882352941176471, 1.0), (0.28627450980392155, 0.011764705882352941, 0.6274509803921569, 1.0), (0.3803921568627451, 0.0, 0.6549019607843137, 1.0), (0.5294117647058824, 0.027450980392156862, 0.6509803921568628, 1.0), (0.7294117647058823, 0.2, 0.5333333333333333, 1.0), (0.8705882352941177, 0.3803921568627451, 0.39215686274509803, 1.0), (0.9019607843137255, 0.4235294117647059, 0.3607843137254902, 1.0), (0.9294117647058824, 0.4745098039215686, 0.3254901960784314, 1.0), (0.996078431372549, 0.7176470588235294, 0.17647058823529413, 1.0)]

# N?EED TO PULL THIS OUT!
import mesaPlot as mp


def make_star_pie(ob_name, R, nr_R, nr_Th, texture_path, phi_start = 0.0, phi_end=30.0, verbose_timing=False):#, \settings, 
    '''Make the geometry for a pie cut from the star'''

    #phi_start, phi_end = 0., 2*np.pi/pie_fraction

    print("** Making an empty to parent to, name=", ob_name)
    bpy.ops.object.empty_add(type="PLAIN_AXES")
    empty = bpy.context.active_object
    empty.name = ob_name
    empty["pie_type"] = "empty"

    print("** Making bool cut!", phi_start, phi_end)
    bool_cut = make_star_pie_for_boolean(ob_name+"bool_cut", R, nr_R, \
                                        nr_Th, -phi_start, -phi_end,)
    bool_cut["pie_type"] = "bool_cut"

    print("** Making the outer sphere")
    sphere = make_outside_star_pie(ob_name+"_outer_sph", R, bool_cut, texture_path)
    sphere.select_set(True)
    sphere["pie_type"] = "outer_sph"

    print("** Making side 1!")
    pie1 = make_pie_side(ob_name+"_pie1", R, nr_R, nr_Th, verbose_timing=verbose_timing)
    pie1.rotation_euler[2] = phi_start
    pie1["pie_type"] = "pie"

    print("** Making side 2")
    pie2 = make_pie_side(ob_name+"_pie2", R, nr_R, nr_Th, verbose_timing=verbose_timing)
    pie2.rotation_euler[2] = phi_start + phi_end
    pie2["pie_type"] = "pie"

    empty.select_set(True)
    bool_cut.select_set(True)
    pie1.select_set(True)
    pie2.select_set(True)
    bpy.context.view_layer.objects.active = empty
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
    bpy.ops.object.select_all(action='DESELECT')

    # Set bool obj to invisible
    bool_cut.hide_viewport = True
    # 2. Hide in Render (The camera icon in the Outliner)
    bool_cut.hide_render = True
    # Optional: Also hide selection in viewport (greyed out)
    bool_cut.hide_select = True 

    # NOW I NEED TO FIX THE LINKING IN THE ADD ON SO THAT YOU CAN CONTROL THE PIE DATA!!!!! 4may26

    return empty

# ######################################################
#
# ######################################################
def make_pie_side(ob_name, R, nr_R, nr_Th, verbose_timing=False):
    '''Make the geometry for one side of the pie cut'''

    mesh_name = "mesh_"+ob_name
    material_name="mat_"+ob_name

    R_mesh = R
    # nr_R = settings.mesh_r_nr_steps #50.
    R_step = R_mesh/nr_R
    R = np.arange(0., R_mesh, R_step) # Excludes R_mesh

    Th_max = np.pi
    # nr_Th = settings.mesh_th_nr_steps #10
    Th_step = Th_max/nr_Th
    Th = np.arange(0., Th_max+Th_step, Th_step) # Includes Th_max
    # Th = np.array([0+i/100*np.pi for i in range(101)])

    # MAKE THE MESH AND VERTS
    if verbose_timing: _ = time()
    verts, edges_radial, edges_th = [], [], []
    vert_col_radial_index, vert_col_th_index = [], []
    vert_index = 0
    vPh = 0.0

    for iTh, vTh in enumerate(Th):
        for iR, vR in enumerate(R):
            x = vR*np.sin(vTh)*np.sin(vPh)
            y = vR*np.sin(vTh)*np.cos(vPh)
            z = vR*np.cos(vTh)
            verts.append((x, y, z))
            # Save the radial index which we need later
            # to set the vertex colors
            vert_col_radial_index.append(iR)
            vert_col_th_index.append(iTh)

            if iR != 0 and iR != len(R):
                edges_radial.append( ( vert_index - 1, vert_index ) )
            if iTh != 0:
                edges_th.append( ( vert_index , vert_index - len(R)) )
            if iTh == len(Th):
                edges_th.append( ( vert_index , vert_index - len(R)) )
            vert_index +=1

    if verbose_timing: print("Timing, make pie, verts: ", time()-_)
    
    if ob_name in bpy.data.objects: # Object exists
        print("Deleting old object")
        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[ob_name].select_set(True)
        bpy.ops.object.delete()
            
        for block in bpy.data.meshes:
            if block.users == 0:
                bpy.data.meshes.remove(block)

        for block in bpy.data.materials:
            if block.users == 0:
                bpy.data.materials.remove(block)

        for block in bpy.data.textures:
            if block.users == 0:
                bpy.data.textures.remove(block)

        for block in bpy.data.images:
            if block.users == 0:
                bpy.data.images.remove(block)
     
    mesh = bpy.data.meshes.new(mesh_name)
    ob = bpy.data.objects.new(ob_name, mesh)

    # # To add vertex colors we add a material to the mesh
    if verbose_timing: _ = time()
    if material_name:
        if material_name in bpy.data.materials:
             mesh.materials.append(bpy.data.materials[material_name])
        else:
             mesh.materials.append(create_material(material_name))#
    if verbose_timing: print("Timing, pie, material", time()-_)

    # Add the verts to the mesh. [] and [] are
    # empty lists saying that we do not have 
    # edges and faces.
    if verbose_timing: _ = time()
    mesh.from_pydata(verts, edges_radial+edges_th, [])
    if verbose_timing: print("Timing, pie, from_pydata", time()-_)

    # Display name and update the mesh
    ob.show_name = False

    mesh.update()
    # Link the object to the collection to see
    # it in the 'Outliner'
    bpy.context.collection.objects.link(ob)

    # The link between the vertex and its index into the radial MESA data we save the 
    # vert_col_radial_index into an attribute
    attribute = mesh.attributes.new(name="vert_col_radial_index", type="INT", domain="POINT")
    attribute_values = [vert_col_radial_index[i] for i in range(len(mesh.vertices))]
    attribute.data.foreach_set("value", attribute_values)

    # Th index in order to later figure it out
    attribute = mesh.attributes.new(name="vert_col_th_index", type="INT", domain="POINT")
    attribute_values = [vert_col_th_index[i] for i in range(len(mesh.vertices))]
    attribute.data.foreach_set("value", attribute_values)

    # Fill_holes:
    if verbose_timing: _ = time()
    bpy.data.objects[ob_name].select_set(True) # Or: bpy.context.view_layer.objects.active = ob
    bpy.context.view_layer.objects.active = bpy.data.objects[ob_name]
    # Go to edit mode
    bpy.ops.object.editmode_toggle()
    # Fill holes to generate faces
    bpy.ops.mesh.select_all(action='SELECT')
    #bpy.ops.mesh.edge_face_add()

    bpy.ops.mesh.fill_holes()
    #bpy.ops.object.mesh.fill_grid(span=1)
    #bpy.ops.object.mesh.fill()

    remove_doubles = True # This will mess up my link to the colors for the vert col.
    if remove_doubles:
        bpy.ops.mesh.remove_doubles()
    
    bpy.ops.object.editmode_toggle()
    if verbose_timing: print("Timing, pie, filling holes etc", time()-_)


    return ob

# ######################################################
# Make star outside
# ######################################################
# Usage:
# make_outside_star_pie("MyStarPie", 1.0, bpy.data.objects["PieShape"], "MyTexture.png")
# Usage Example:
# make_outside_star_pie("MyCutSphere", 1.0, bpy.data.objects["MyPieObject"])
# Usage Example:
# make_outside_star_pie("MyCutSphere", 1.0, bpy.data.objects["MyPieObject"])
def make_outside_star_pie(ob_name, R, pie_for_boolean, texture_path, material_name="outer_shell_mat"):
    # 1. Create a UV Sphere
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=R,
        location=(0, 0, 0),
        segments=32,
        ring_count=16
    )
    sphere = bpy.context.active_object
    sphere.name = ob_name

    # 2. Shade the sphere smooth
    bpy.ops.object.shade_smooth()

    # 3. Add a Boolean Modifier
    if pie_for_boolean:
        bool_mod = sphere.modifiers.new(name="Boolean", type='BOOLEAN')
        bool_mod.operation = 'INTERSECT'  # Options: 'INTERSECT', 'UNION', 'DIFFERENCE'
        bool_mod.object = pie_for_boolean
    else:
        print("Warning: Boolean object 'YourBooleanObject' not found!")




    # 4. Add a Texture (using Node-based Material)
    # Create a new material
    if False:
        material = bpy.data.materials.new(name=ob_name+"_mat")
        material.use_nodes = True
        sphere.data.materials.append(material)

        # Get the principled BSDF node
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Clear default nodes
        nodes.clear()

        # Create new nodes
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        output = nodes.new(type='ShaderNodeOutputMaterial')

        # Connect them
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

        # Add a texture (Image Texture example)
        texture_node = nodes.new(type='ShaderNodeTexImage')
        texture_node.image = bpy.data.images.get(texture_path)  # Replace with your image

        # Connect texture to base color
        links.new(texture_node.outputs['Color'], bsdf.inputs['Base Color'])

        # Optional: Add UV mapping for the texture
        uv_map = nodes.new(type='ShaderNodeTexCoord')
        links.new(uv_map.outputs['UV'], texture_node.inputs['Vector'])



    bpy.context.view_layer.objects.active = sphere
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    threshold_radius = R*0.985

    # Access the mesh data
    mesh = sphere.data
    # bmesh = None

    bm = bmesh.from_edit_mesh(mesh)
    
    # Iterate through vertices and mark for deletion
    verts_to_delete = []
    for v in bm.verts:
        # Calculate distance from world origin (0,0,0)
        # Note: If sphere moved, use v.co transformed by matrix_world
        dist = math.sqrt(v.co.x**2 + v.co.y**2 + v.co.z**2)
        
        if dist < threshold_radius:
        # if dist != R:
            v.select = True
            verts_to_delete.append(v)
            
    # Delete selected vertices
    if verts_to_delete:
        bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')
        bmesh.update_edit_mesh(mesh)
        print(f"Deleted {len(verts_to_delete)} inner vertices.")
    else:
        print("No vertices found within the threshold radius.")

    # Create vertex colors
    bpy.ops.object.mode_set(mode='OBJECT')

    # # To add vertex colors we add a material to the mesh
    # if verbose_timing: _ = time()
    if material_name:
        if material_name in bpy.data.materials:
             mesh.materials.append(bpy.data.materials[material_name])
        else:
             mesh.materials.append(create_material(material_name))#
    # if verbose_timing: print("Timing, pie, material", time()-_)


    return sphere

# ######################################################
# Make star pie for boolean cut out
# ######################################################
def make_star_pie_for_boolean(ob_name, R, nr_R, nr_Th, phi_start, phi_end, verbose_timing=False):#, \settings, 
                  # material_name = 'mat_vertex_colors'):
    # ob_name = settings.ob_name
    mesh_name = "mesh_"+ob_name
    material_name="mat_"+ob_name

    R_mesh = R#10.
    # nr_R = settings.mesh_r_nr_steps #50.
    R_step = 10./nr_R
    R = np.arange(0., R_mesh, R_step) # Excludes R_mesh

    Th_max = np.pi
    # nr_Th = settings.mesh_th_nr_steps #10
    Th_step = Th_max/nr_Th
    Th = np.arange(0., Th_max+Th_step, Th_step) # Includes Th_max
    # Th = np.array([0+i/100*np.pi for i in range(101)])

    nrPh = 50
    # pie_fraction = 8
    
    Ph = np.array([phi_start+i/nrPh*phi_end for i in range(nrPh+1)])
    # Ph = np.array([0+i/nrPh*2*np.pi/pie_fraction for i in range(nrPh+1)])
    #np.array([0, 2*np.pi/8])#+i/10*2*np.pi/4. for i in range(10)])
    #R = np.array([i/10 for i in range(150)])

    # MAKE THE MESH AND VERTS
    if verbose_timing: _ = time()
    verts, edges_radial, edges_th = [], [], []
    vert_col_radial_index = []
    vert_index = 0
    for iPh, vPh in enumerate(Ph):
        for iTh, vTh in enumerate(Th):
            for iR, vR in enumerate(R):
                if (vPh == Ph[0]) or (vPh == Ph[-1]):
                    x = vR*np.sin(vTh)*np.sin(vPh)
                    y = vR*np.sin(vTh)*np.cos(vPh)
                    z = vR*np.cos(vTh)
                    verts.append((x, y, z))
                    # Save the radial index which we need later
                    # to set the vertex colors
                    vert_col_radial_index.append(iR)

                    if iR != 0 and iR != len(R):
                        edges_radial.append( ( vert_index - 1, vert_index ) )
                    if iTh != 0:
                        edges_th.append( ( vert_index , vert_index - len(R)) )
                    if iTh == len(Th):
                        edges_th.append( ( vert_index , vert_index - len(R)) )
                    vert_index +=1

    for iPh, vPh in enumerate(Ph):
        for iTh, vTh in enumerate(Th):
            vR = R[-1]
            x = vR*np.sin(vTh)*np.sin(vPh)
            y = vR*np.sin(vTh)*np.cos(vPh)
            z = vR*np.cos(vTh)

            verts.append((x, y, z))
            # Save the radial index which we need later
            # to set the vertex colors
            # Since it is on the max radius, set it to the
            # last index
            vert_col_radial_index.append(-1)

            if iTh != len(Th):
                edges_th.append( ( vert_index-1 , vert_index) )
            if iPh != 0:
                edges_th.append( ( vert_index , vert_index - len(Th)) )
            vert_index +=1
            # This way of doing leaves some double vertices at R=max and Ph=max. 
            # But later we remove duplicates after creating edges and faces. This way
            # Blender fixes things.
    if verbose_timing: print("Timing, make pie, verts: ", time()-_)
    
    if ob_name in bpy.data.objects: # Object exists
        print("Deleting old object")
        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[ob_name].select_set(True)
        bpy.ops.object.delete()
            
        for block in bpy.data.meshes:
            if block.users == 0:
                bpy.data.meshes.remove(block)

        for block in bpy.data.materials:
            if block.users == 0:
                bpy.data.materials.remove(block)

        for block in bpy.data.textures:
            if block.users == 0:
                bpy.data.textures.remove(block)

        for block in bpy.data.images:
            if block.users == 0:
                bpy.data.images.remove(block)
     
    mesh = bpy.data.meshes.new(mesh_name)
    ob = bpy.data.objects.new(ob_name, mesh)

    # # # To add vertex colors we add a material to the mesh
    # if verbose_timing: _ = time()
    # if material_name:
    #     if material_name in bpy.data.materials:
    #          mesh.materials.append(bpy.data.materials[material_name])
    #     else:
    #          mesh.materials.append(create_material(material_name))#
    # if verbose_timing: print("Timing, pie, material", time()-_)

    # # Add the verts to the mesh. [] and [] are
    # # empty lists saying that we do not have 
    # # edges and faces.
    if verbose_timing: _ = time()
    mesh.from_pydata(verts, edges_radial+edges_th, [])
    if verbose_timing: print("Timing, pie, from_pydata", time()-_)

    # # Display name and update the mesh
    ob.show_name = False

    mesh.update()
    # Link the object to the collection to see
    # it in the 'Outliner'
    bpy.context.collection.objects.link(ob)

    # # The link between the vertex and its index into the radial MESA data we save the 
    # # vert_col_radial_index into an attribute
    # attribute = mesh.attributes.new(name="vert_col_radial_index", type="INT", domain="POINT")
    # attribute_values = [vert_col_radial_index[i] for i in range(len(mesh.vertices))]
    # attribute.data.foreach_set("value", attribute_values)

    # Fill_holes:
    if verbose_timing: _ = time()
    bpy.data.objects[ob_name].select_set(True) # Or: bpy.context.view_layer.objects.active = ob
    bpy.context.view_layer.objects.active = bpy.data.objects[ob_name]
    # Go to edit mode
    bpy.ops.object.editmode_toggle()
    # Fill holes to generate faces
    bpy.ops.mesh.select_all(action='SELECT')
    #bpy.ops.mesh.edge_face_add()

    bpy.ops.mesh.fill_holes()
    #bpy.ops.object.mesh.fill_grid(span=1)
    #bpy.ops.object.mesh.fill()

    remove_doubles = True # This will mess up my link to the colors for the vert col.
    if remove_doubles:
        bpy.ops.mesh.remove_doubles()
    
    bpy.ops.object.editmode_toggle()
    if verbose_timing: print("Timing, pie, filling holes etc", time()-_)


    return ob



# ######################################################
def make_chem_vertex_colors(r, v, ob, labels, nr_Th, vertex_colors_name_base="test_v_colors", verbose=False):
# ######################################################

    mesh = ob.data

    # Check if there is a vertex_color attribute and 
    # if yes check if the name already exists
    if not mesh.vertex_colors:
        print("  New vertex_colors")
        mesh.vertex_colors.new(name=vertex_colors_name_base)
        color_layer = mesh.vertex_colors[vertex_colors_name_base]
    else:
        if not vertex_colors_name_base in mesh.vertex_colors:
            print("  New vertex_colors because diff name")
            mesh.vertex_colors.new(name=vertex_colors_name_base)
            color_layer = mesh.vertex_colors[vertex_colors_name_base]
        else:
            color_layer = mesh.vertex_colors[vertex_colors_name_base]

    # Start walking over the polygons and loop indices
    list_color = []

    # cmap = CMAP_BASE
    # CMAP_DEFAULT = cmr.get_sub_cmap("cmr.pride", 0, 0.8)
    # cmap = plt.get_cmap(CMAP_DEFAULT, len(labels))


    for poly in mesh.polygons:
        for vert_i_poly, vert_i_mesh in enumerate(poly.vertices):
            r_index = mesh.attributes['vert_col_radial_index'].data[vert_i_mesh].value
            th_index = mesh.attributes['vert_col_th_index'].data[vert_i_mesh].value
            
            # tot = np.sum(v[:, r_index])
            hydrogen_profile = v[labels.index('h1'), r_index]
            helium_profile = v[labels.index('he3'), r_index]

            abundances = np.array([i for i in v[:, r_index]])*nr_Th

            print("ABUND STUFF", f"{len(abundances)=} {len(CMAP_RGBA)=}")
            abundances_cummulative = np.array([np.sum(abundances[0:i+1]) for i in range(len(abundances))])
            print("ABUND STUFF", f"{len(abundances_cummulative)=}")
            idx = np.searchsorted(abundances_cummulative, th_index)
            print("ABUND STUFF", f"{idx=}")
            vert_color = CMAP_RGBA[idx]



            # if th_index < hydrogen_profile*nr_Th:#hydrogen_profile[r_index]*nr_Th:
            #     vert_color = CMAP_RGBA[0]#[1, 0, 0, 1] #Hydrogen
            # elif (hydrogen_profile*nr_Th < th_index) and \
            #     (th_index < (hydrogen_profile+helium_profile)*nr_Th):
            # # elif hydrogen_profile[r_index]*nr_Th < th_index < (hydrogen_profile[r_index]+helium_profile[r_index])*nr_Th:
            #     vert_color = CMAP_RGBA[1]#[0, 1, 0, 1] #Helium
            # else:
            #     vert_color = CMAP_RGBA[-1]#[0, 0, 1, 1] #Rest


            list_color.append(
                vert_color
                )
    color_layer.data.foreach_set("color", np.array(list_color).flatten())



# ######################################################
def make_vertex_colors(r, v, ob, vertex_colors_name_base="test_v_colors", verbose=False):
# ######################################################

    mesh = ob.data

    # Check if there is a vertex_color attribute and 
    # if yes check if the name already exists
    if not mesh.vertex_colors:
        print("  New vertex_colors")
        mesh.vertex_colors.new(name=vertex_colors_name_base)
        color_layer = mesh.vertex_colors[vertex_colors_name_base]
    else:
        if not vertex_colors_name_base in mesh.vertex_colors:
            print("  New vertex_colors because diff name")
            mesh.vertex_colors.new(name=vertex_colors_name_base)
            color_layer = mesh.vertex_colors[vertex_colors_name_base]
        else:
            color_layer = mesh.vertex_colors[vertex_colors_name_base]

    # print(ob, ob.data, mesh.vertex_colors)

    list_color = []
    p = mp.plot(rcparams_fixed=False)
    cmap = p.mergeCmaps([plt.cm.Purples_r, plt.cm.hot_r], [[0.0, 0.5], [0.5, 1.0]])
    cmin, cmax = -10, 10 #min(value), max(value)
    norm = Normalize(vmin=cmin, vmax=cmax)

    if verbose: _ = time()
    # For each loop index of the vertex we get the radial indices into the MESA data 
    # We saved these indices when we made the geometry and mesh and stored it in the 
    # attribute vert_col_radial_index.
    list_color = [v[mesh.attributes['vert_col_radial_index'].data[vert_i_mesh].value] \
            for poly in mesh.polygons\
            for vert_i_poly, vert_i_mesh in enumerate(poly.vertices)]
    
    list_color = np.array(list_color)
    list_color = cmap(norm( list_color ))
    if verbose: print("time list_color", time()-_)
    print("pie", list_color)
    if verbose: _ = time()
    color_layer.data.foreach_set("color", list_color.flatten())
    if verbose: print("time foreach_set", time()-_)


        # # # poly.vertices: length is the amount of vertices in the polygon
        # # #                the values of the elements are the indeces to the vertices in the mesh
        # # # poly.loop_indices:    - length is also the amount of vertices in the polygon
        # # #                       - the values of the elements is an index that takes every vertex in a polygon as one unit
        # # #                         This is useful because every vertex can have a different color in each polygon that it is part of.
        # # #                         Thus color_layer.data can be indexed using the values in loop_index.

        # # # Every vertex has two indices associated with it. A vertex has one index which is unique for 
        # # # the vertex and is used to get the vertex from the mesh (for example to get coordinates of a vertex: 
        # # # bpy.data.meshes['Cube'].vertices.data.vertices[0].co). 
        # # # A vertex can have (multi) indices of a second kind, often called the loop index. The vertex can be part
        # # # of multiple faces (often called polygons) and for every face it is part of it has a different loop indices.
        # # # Because a vertex can have a different vertex color for for every face it is part of, 
        # # # mesh.vertex_colors[vertex_colors_name].data is indexed with the loop indices. 

# ######################################################
def make_vertex_colors_surface(ob, eff_temp_color, vertex_colors_name_base="test_surface_colors", verbose=False):
# ######################################################

    mesh = ob.data

    # Check if there is a vertex_color attribute and 
    # if yes check if the name already exists
    if not mesh.vertex_colors:
        print("  New vertex_colors")
        mesh.vertex_colors.new(name=vertex_colors_name_base)
        color_layer = mesh.vertex_colors[vertex_colors_name_base]
    else:
        if not vertex_colors_name_base in mesh.vertex_colors:
            print("  New vertex_colors because diff name")
            mesh.vertex_colors.new(name=vertex_colors_name_base)
            color_layer = mesh.vertex_colors[vertex_colors_name_base]
        else:
            color_layer = mesh.vertex_colors[vertex_colors_name_base]

    # print(ob, ob.data, mesh.vertex_colors)

    # list_color = []
    # p = mp.plot(rcparams_fixed=False)
    # cmap = p.mergeCmaps([plt.cm.Purples_r, plt.cm.hot_r], [[0.0, 0.5], [0.5, 1.0]])
    # cmin, cmax = 0, 1.  #min(value), max(value)
    # norm = Normalize(vmin=cmin, vmax=cmax)

    # if verbose: _ = time()
    # # For each loop index of the vertex we get the radial indices into the MESA data 
    # # We saved these indices when we made the geometry and mesh and stored it in the 
    # # attribute vert_col_radial_index.
    # list_color = np.array([[0.5, 0., 0., 1.0] \
    #         for poly in mesh.polygons\
    #         for vert_i_poly, vert_i_mesh in enumerate(poly.vertices)])
    
    # We loop over all the polygons
    for poly in mesh.polygons:
        # We get the polygon index and the corresponding mesh index
        for vert_i_poly, vert_i_mesh in enumerate(poly.vertices):  
            # We get the loop index from the polygon index   
            vert_i_loop = poly.loop_indices[vert_i_poly]
            # We set the color for the vertex
            color_layer.data[vert_i_loop].color = eff_temp_color#[1., 1., 0., 1.0]#vert_colors[vert_i_loop]
            # A print statement to see how the indices relate to each other 
            # print(list(color_layer.data[vert_i_loop].color), vert_i_poly, vert_i_mesh, vert_i_loop)

    # list_color = np.array(list_color)
    # list_color = cmap(norm( list_color ))
    # if verbose: print("time list_color", time()-_)
    # print("siurface", list_color)
    # if verbose: _ = time()
    # color_layer.data.foreach_set("color", list_color.flatten())
    # if verbose: print("time foreach_set", time()-_)


        # # # poly.vertices: length is the amount of vertices in the polygon
        # # #                the values of the elements are the indeces to the vertices in the mesh
        # # # poly.loop_indices:    - length is also the amount of vertices in the polygon
        # # #                       - the values of the elements is an index that takes every vertex in a polygon as one unit
        # # #                         This is useful because every vertex can have a different color in each polygon that it is part of.
        # # #                         Thus color_layer.data can be indexed using the values in loop_index.

        # # # Every vertex has two indices associated with it. A vertex has one index which is unique for 
        # # # the vertex and is used to get the vertex from the mesh (for example to get coordinates of a vertex: 
        # # # bpy.data.meshes['Cube'].vertices.data.vertices[0].co). 
        # # # A vertex can have (multi) indices of a second kind, often called the loop index. The vertex can be part
        # # # of multiple faces (often called polygons) and for every face it is part of it has a different loop indices.
        # # # Because a vertex can have a different vertex color for for every face it is part of, 
        # # # mesh.vertex_colors[vertex_colors_name].data is indexed with the loop indices. 


# ######################################################
# MAKE BLENDER MATERIALS AND NODES
# ######################################################
def create_material(name):
    # Make material
    mat = bpy.data.materials.new(name)
    mat.blend_method = 'BLEND' # Alpha Blend, Render polygon transparent, depending on alpha channel of the texture.
    mat.use_nodes = True
    mat.show_transparent_back = False
    nodes = mat.node_tree.nodes

    # clear all nodes to start clean
    nodes.clear()

    # This attribute will be controlled by Geometry Nodes
    # It will write the vertex color to "layer_name" as a function of frame nr
    node_vertex_color = nodes.new(type='ShaderNodeVertexColor')
    node_vertex_color.location = -400, 150
    node_vertex_color.layer_name = "" 
    
    # Transparency BSDF shader
    node_BSDF_transparency = nodes.new(type='ShaderNodeBsdfTransparent')
    node_BSDF_transparency.location = -200, 300

    # BSDF SHader Diffuse
    node_emission = nodes.new(type='ShaderNodeEmission')#ShaderNodeBsdfDiffuse')
    node_emission.inputs[1].default_value = 0.5
    node_emission.location = -200, 60

    # Mixer
    node_shader_mixer = nodes.new(type='ShaderNodeMixShader')
    node_shader_mixer.inputs[0].default_value = 1.0
    node_shader_mixer.location = 50, 180

    # Output
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_output.location = 250, 180

    # # link nodes
    links = mat.node_tree.links
    link = links.new(node_vertex_color.outputs[0], node_emission.inputs[0])
    link2 = links.new(node_emission.outputs[0], node_shader_mixer.inputs[2])
    link3 = links.new(node_BSDF_transparency.outputs[0], node_shader_mixer.inputs[1])
    link5 = links.new(node_shader_mixer.outputs[0], node_output.inputs[0])
    return mat



def make_vertex_colors_old(r, v, ob_name, vertex_colors_name_base="test_v_colors"):

    ob = bpy.data.objects[ob_name]
    mesh = ob.data

    # for i, _ in enumerate(data_values):
    # print("v cols", i)
    radius, value = r, v#_
    radius = [0., *radius]
    value = [value[0], *value]
    interp_value = interp1d(radius, value)#, kind='cubic')
    R_star = np.max(radius)
    # iT = ob.stellarProperties.T_index[i]
    # R_star = ob.stellarProperties.R_star[i]

    vertex_colors_name = vertex_colors_name_base#+"_"+str(i)

    # Check if there is a vertex_color attribute and 
    # if yes check if the name already exists
    if not mesh.vertex_colors:
        mesh.vertex_colors.new(name=vertex_colors_name)
        color_layer = mesh.vertex_colors[vertex_colors_name]
    else:
        if not vertex_colors_name in mesh.vertex_colors:
            mesh.vertex_colors.new(name=vertex_colors_name)
            color_layer = mesh.vertex_colors[vertex_colors_name]
        else:
            color_layer = mesh.vertex_colors[vertex_colors_name]

    p = mp.plot(rcparams_fixed=False)
    cmap = p.mergeCmaps([plt.cm.Purples_r, plt.cm.hot_r], [[0.0, 0.5], [0.5, 1.0]])
    cmin, cmax = -10, 10 #min(value), max(value)
    norm = Normalize(vmin=cmin, vmax=cmax)
    for poly in mesh.polygons:
        for vert_i_poly, vert_i_mesh in enumerate(poly.vertices):#loop_indices:
            #rgb = [random.random(),0,0,0]
            vert_i_loop = poly.loop_indices[vert_i_poly]

            r = np.linalg.norm(ob.data.vertices[vert_i_mesh].co)/10.
            color = cmap(norm(interp_value(r * R_star)))
            color_layer.data[vert_i_loop].color = color#(interp_value(r * R_star),0,0,0)#(r, r,0,0)#(interp_value(r/15 * R_star),0,0,0)#vert_colors[vert_i_mesh]#rgb


        # # # poly.vertices: length is the amount of vertices in the polygon
        # # #                the values of the elements are the indeces to the vertices in the mesh
        # # # poly.loop_indices:    - length is also the amount of vertices in the polygon
        # # #                       - the values of the elements is an index that takes every vertex in a polygon as one unit
        # # #                         This is useful because every vertex can have a different color in each polygon that it is part of.
        # # #                         Thus color_layer.data can be indexed using the values in loop_index.

        # # # Every vertex has two indices associated with it. A vertex has one index which is unique for 
        # # # the vertex and is used to get the vertex from the mesh (for example to get coordinates of a vertex: 
        # # # bpy.data.meshes['Cube'].vertices.data.vertices[0].co). 
        # # # A vertex can have (multi) indices of a second kind, often called the loop index. The vertex can be part
        # # # of multiple faces (often called polygons) and for every face it is part of it has a different loop indices.
        # # # Because a vertex can have a different vertex color for for every face it is part of, 
        # # # mesh.vertex_colors[vertex_colors_name].data is indexed with the loop indices. 

