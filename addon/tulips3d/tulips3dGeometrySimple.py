
# if "bpy" in locals():
#     import importlib
#     importlib.reload(colormodels)
# else:
#     from . import colormodels

import bpy
import bmesh

import numpy as np
import math
import sys
from time import time
# import matplotlib.pyplot as plt
# from matplotlib.colors import ListedColormap, to_rgb
# from matplotlib.colors import Normalize, LogNorm
# from scipy.interpolate import interp1d



def make_star_pie(ob_name, R, nr_R, nr_Th, texture_path, phi_start = 0.0, phi_step=30.0, verbose_timing=False):#, \settings, 
    '''Make the geometry for a pie cut from the star'''

    #phi_start, phi_end = 0., 2*np.pi/pie_fraction

    print("** Making an empty to parent to, name=", ob_name)
    bpy.ops.object.empty_add(type="PLAIN_AXES")
    empty = bpy.context.active_object
    empty.name = ob_name
    empty["pie_type"] = "empty"

    print("** Making bool cut!", phi_start, phi_step)
    bool_cut = make_star_pie_for_boolean(ob_name+"bool_cut", R, nr_R, \
                                        nr_Th, -0, -phi_step,)
    #nr_Th, -phi_start, -phi_step,)
    bool_cut["pie_type"] = "bool_cut"

    print("** Making the outer sphere")
    sphere = make_outside_star_pie(ob_name+"_outer_sph", R, bool_cut, texture_path)
    sphere.select_set(True)
    sphere["pie_type"] = "outer_sph"

    print("** Making side 1!")
    pie1 = make_pie_side(ob_name+"_pie1", R, nr_R, nr_Th, verbose_timing=verbose_timing)
    pie1.rotation_euler[2] = 0#phi_start
    pie1["pie_type"] = "pie"

    print("** Making side 2")
    pie2 = make_pie_side(ob_name+"_pie2", R, nr_R, nr_Th, verbose_timing=verbose_timing)
    pie2.rotation_euler[2] = 0 + phi_step #phi_start + phi_step
    pie2["pie_type"] = "pie"

    empty.select_set(True)
    bool_cut.select_set(True)
    pie1.select_set(True)
    pie2.select_set(True)
    bpy.context.view_layer.objects.active = empty
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
    bpy.ops.object.select_all(action='DESELECT')

    empty.rotation_euler[2] = phi_start

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

    # # # To add vertex colors we add a material to the mesh
    # if verbose_timing: _ = time()
    # if material_name:
    #     if material_name in bpy.data.materials:
    #          mesh.materials.append(bpy.data.materials[material_name])
    #     else:
    #          mesh.materials.append(create_material(material_name))#
    # if verbose_timing: print("Timing, pie, material", time()-_)

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
    # attribute = mesh.attributes.new(name="vert_col_radial_index", type="INT", domain="POINT")
    # attribute_values = [vert_col_radial_index[i] for i in range(len(mesh.vertices))]
    # attribute.data.foreach_set("value", attribute_values)

    # # Th index in order to later figure it out
    # attribute = mesh.attributes.new(name="vert_col_th_index", type="INT", domain="POINT")
    # attribute_values = [vert_col_th_index[i] for i in range(len(mesh.vertices))]
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
    # if material_name:
    #     if material_name in bpy.data.materials:
    #          mesh.materials.append(bpy.data.materials[material_name])
    #     else:
    #          mesh.materials.append(create_material(material_name))#
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