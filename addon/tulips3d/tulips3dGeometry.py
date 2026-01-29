
if "bpy" in locals():
    import importlib
    importlib.reload(colormodels)
else:
    from . import colormodels

import bpy
import numpy as np
import sys
from time import time
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LogNorm
from scipy.interpolate import interp1d

# N?EED TO PULL THIS OUT!
import mesaPlot as mp

def make_star_pie(ob_name, nr_R, nr_Th, verbose_timing=False):#, \settings, 
                  # material_name = 'mat_vertex_colors'):
    # ob_name = settings.ob_name
    mesh_name = "mesh_"+ob_name
    material_name="mat_"+ob_name

    R_mesh = 10.
    # nr_R = settings.mesh_r_nr_steps #50.
    R_step = 10./nr_R
    R = np.arange(0., R_mesh, R_step) # Excludes R_mesh

    Th_max = np.pi
    # nr_Th = settings.mesh_th_nr_steps #10
    Th_step = Th_max/nr_Th
    Th = np.arange(0., Th_max+Th_step, Th_step) # Includes Th_max
    # Th = np.array([0+i/100*np.pi for i in range(101)])

    nrPh = 50
    pie_fraction = 8
    Ph = np.array([0+i/nrPh*2*np.pi/pie_fraction for i in range(nrPh+1)])
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

    attribute = mesh.attributes.new(name="vert_col_radial_index", type="INT", domain="POINT")
    attribute_values = [vert_col_radial_index[i] for i in range(len(mesh.vertices))]
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

# def make_vertex_colors(data_values, ob_name, vertex_colors_name_base):
# def make_vertex_colors(r, v, settings, vertex_colors_name_base="test_v_colors"):
def make_vertex_colors(r, v, ob_name, vertex_colors_name_base="test_v_colors"):
# bpy.data.objects['Star_Pie'].data.attributes['vert_col_radial_index'].data[10].value

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
            
            ind = mesh.attributes['vert_col_radial_index'].data[vert_i_mesh].value
            
            #r = np.linalg.norm(ob.data.vertices[vert_i_mesh].co)/10.
            color = cmap(norm(v[ind]))
            # color = cmap(norm(interp_value(r * R_star)))

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




# def make_vertex_colors(r, v, ob_name, vertex_colors_name_base="test_v_colors"):

#     ob = bpy.data.objects[ob_name]
#     mesh = ob.data

#     # for i, _ in enumerate(data_values):
#     # print("v cols", i)
#     radius, value = r, v#_
#     radius = [0., *radius]
#     value = [value[0], *value]
#     interp_value = interp1d(radius, value)#, kind='cubic')
#     R_star = np.max(radius)
#     # iT = ob.stellarProperties.T_index[i]
#     # R_star = ob.stellarProperties.R_star[i]

#     vertex_colors_name = vertex_colors_name_base#+"_"+str(i)

#     # Check if there is a vertex_color attribute and 
#     # if yes check if the name already exists
#     if not mesh.vertex_colors:
#         mesh.vertex_colors.new(name=vertex_colors_name)
#         color_layer = mesh.vertex_colors[vertex_colors_name]
#     else:
#         if not vertex_colors_name in mesh.vertex_colors:
#             mesh.vertex_colors.new(name=vertex_colors_name)
#             color_layer = mesh.vertex_colors[vertex_colors_name]
#         else:
#             color_layer = mesh.vertex_colors[vertex_colors_name]

#     p = mp.plot(rcparams_fixed=False)
#     cmap = p.mergeCmaps([plt.cm.Purples_r, plt.cm.hot_r], [[0.0, 0.5], [0.5, 1.0]])
#     cmin, cmax = -10, 10 #min(value), max(value)
#     norm = Normalize(vmin=cmin, vmax=cmax)
#     for poly in mesh.polygons:
#         for vert_i_poly, vert_i_mesh in enumerate(poly.vertices):#loop_indices:
#             #rgb = [random.random(),0,0,0]
#             vert_i_loop = poly.loop_indices[vert_i_poly]

#             r = np.linalg.norm(ob.data.vertices[vert_i_mesh].co)/10.
#             color = cmap(norm(interp_value(r * R_star)))
#             color_layer.data[vert_i_loop].color = color#(interp_value(r * R_star),0,0,0)#(r, r,0,0)#(interp_value(r/15 * R_star),0,0,0)#vert_colors[vert_i_mesh]#rgb


#         # # # poly.vertices: length is the amount of vertices in the polygon
#         # # #                the values of the elements are the indeces to the vertices in the mesh
#         # # # poly.loop_indices:    - length is also the amount of vertices in the polygon
#         # # #                       - the values of the elements is an index that takes every vertex in a polygon as one unit
#         # # #                         This is useful because every vertex can have a different color in each polygon that it is part of.
#         # # #                         Thus color_layer.data can be indexed using the values in loop_index.

#         # # # Every vertex has two indices associated with it. A vertex has one index which is unique for 
#         # # # the vertex and is used to get the vertex from the mesh (for example to get coordinates of a vertex: 
#         # # # bpy.data.meshes['Cube'].vertices.data.vertices[0].co). 
#         # # # A vertex can have (multi) indices of a second kind, often called the loop index. The vertex can be part
#         # # # of multiple faces (often called polygons) and for every face it is part of it has a different loop indices.
#         # # # Because a vertex can have a different vertex color for for every face it is part of, 
#         # # # mesh.vertex_colors[vertex_colors_name].data is indexed with the loop indices. 

