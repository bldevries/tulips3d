bl_info = {
    "name": "Tulips3D",
    "author": "B.L. de Vries",
    "version": (0, 0, 1),
    "blender": (4, 5, 0),          # <-- target version
    "location": "Properties > Scene",
    "description": "Adds a 3d visualisation of the output of the MESA stellar evolution code.",
    "category": "Object",
}

import bpy
import numpy as np
import sys
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LogNorm

import mesaPlot as mp

from bpy.props import (
    FloatProperty,
    StringProperty,
    IntProperty,
    EnumProperty,
    CollectionProperty
)


def make_star_pie(ob_name = 'disk'):#, \
                  # material_name = 'mat_vertex_colors'):

    mesh_name = "mesh_"+ob_name
    material_name="mat_"+ob_name


    Th = np.array([0+i/100*np.pi for i in range(101)])
    nrPh = 50
    pie_fraction = 8
    Ph = np.array([0+i/nrPh*2*np.pi/pie_fraction for i in range(nrPh+1)])
    #np.array([0, 2*np.pi/8])#+i/10*2*np.pi/4. for i in range(10)])
    R = np.array([i/10 for i in range(150)])

    # MAKE THE MESH AND VERTS
    verts, edges_radial, edges_th = [], [], []
    vert_index = 0
    for iPh, vPh in enumerate(Ph):
        for iTh, vTh in enumerate(Th):
            for iR, vR in enumerate(R):
                if (vPh == Ph[0]) or (vPh == Ph[-1]):
                    x = vR*np.sin(vTh)*np.sin(vPh)
                    y = vR*np.sin(vTh)*np.cos(vPh)
                    z = vR*np.cos(vTh)
                    verts.append((x, y, z))

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

            if iTh != len(Th):
                edges_th.append( ( vert_index-1 , vert_index) )
            if iPh != 0:
                edges_th.append( ( vert_index , vert_index - len(Th)) )
            vert_index +=1
            # This way of doing leaves some double vertices at R=max and Ph=max. 
            # But later we remove duplicates after creating edges and faces. This way
            # Blender fixes things.

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

    if material_name:
        if material_name in bpy.data.materials:
             mesh.materials.append(bpy.data.materials[material_name])
        else:
             mesh.materials.append(create_material(material_name))#

    # Add the verts to the mesh. [] and [] are
    # empty lists saying that we do not have 
    # edges and faces.
    mesh.from_pydata(verts, edges_radial+edges_th, [])

    # Display name and update the mesh
    ob.show_name = False

    mesh.update()
    # Link the object to the collection to see
    # it in the 'Outliner'
    bpy.context.collection.objects.link(ob)

    # Fill_holes:
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
    bpy.ops.mesh.remove_doubles()
    bpy.ops.object.editmode_toggle()

    return ob

def make_vertex_colors():
    print()


# ######################################################
# MAKE BLENDER MATERIALS AND NODES
# ######################################################
def create_geometrynodes(name):
    print()



def create_material(name):
    # Make material
    mat = bpy.data.materials.new(name)
    mat.blend_method = 'BLEND' # Alpha Blend, Render polygon transparent, depending on alpha channel of the texture.
    mat.use_nodes = True
    mat.show_transparent_back = False
    nodes = mat.node_tree.nodes

    # clear all nodes to start clean
    nodes.clear()

    # # Make nodes
    # # Color input for the Diffuse BSDF shader
    # # node_attr = nodes.new(type='ShaderNodeAttribute')
    # # node_attr.location = -400, 60
    # # node_attr.attribute_name = vertex_colors_name

    # Vertex color Alpha input for transparency
    # node_vertex_color_transparency = nodes.new(type='ShaderNodeVertexColor')
    # node_vertex_color_transparency.location = -200, 300
    # node_vertex_color_transparency.layer_name = vertex_colors_name

    
    # This attribute will be controlled by Geometry Nodes
    # It will write the vertex color to "layer_name" as a function of frame nr
    node_vertex_color = nodes.new(type='ShaderNodeVertexColor')
    node_vertex_color.location = -400, 150
    node_vertex_color.layer_name = "" 
    
    # Transparency BSDF shader
    node_BSDF_transparency = nodes.new(type='ShaderNodeBsdfTransparent')
    node_BSDF_transparency.location = -200, 300

    # BSDF SHader Diffuse
    node_BSDF_diff = nodes.new(type='ShaderNodeBsdfDiffuse')
    node_BSDF_diff.location = -200, 60

    # Mixer
    node_shader_mixer = nodes.new(type='ShaderNodeMixShader')
    node_shader_mixer.inputs[0].default_value = 1.0
    node_shader_mixer.location = 50, 180

    # Output
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_output.location = 250, 180

    # # link nodes
    links = mat.node_tree.links
    link = links.new(node_vertex_color.outputs[0], node_BSDF_diff.inputs[0])
    link2 = links.new(node_BSDF_diff.outputs[0], node_shader_mixer.inputs[2])
    link3 = links.new(node_BSDF_transparency.outputs[0], node_shader_mixer.inputs[1])
    # link4 = links.new(node_vertex_color.outputs[1], node_shader_mixer.inputs[0])
    link5 = links.new(node_shader_mixer.outputs[0], node_output.inputs[0])
    return mat

# ######################################################
# MESA DATA 
# ######################################################
def prepare_energy_data(file_path_mesa_data):
    '''Reads in Energy production data from a mesa file'''

    # We use mesaplot to read in the mesa data
    m = mp.MESA() # Create MESA object
    m.loadHistory(f=file_path_mesa_data)
    
    # We need these indices for the burning data
    qtop = "burn_qtop_"
    qtype = "burn_type_"

    # A check if data is avaliable
    try:
        m.hist.data[qtop + "1"]
    except ValueError:
        raise KeyError(
            "No field " + qtop + "* found, add mixing_regions 40 and burning_regions 40 to your history_columns.list")

    star_masses = sm = m.hist.star_mass
    time_indices = len(star_masses)

    data_values = []
    R_star = []
    T_index = []
    for start_ind in range(time_indices):
        num_burn_zones = int([xx.split('_')[2] for xx in m.hist.data.dtype.names if qtop in xx][-1])
        # Per time stamp we will have radii and values, which we list in these variables:
        list_r, list_value = [], []
        for region in range(1, num_burn_zones + 1):
            radius = np.abs(m.hist.data[qtop + str(region)][start_ind] * sm[start_ind])
            burn = m.hist.data[qtype + str(region)][start_ind]
            list_r.append(radius)
            list_value.append(burn)
        # We make one data array
        _d = np.array([list_r, list_value])
        # We need to remove duplicates at the end where value==-9999
        _mask = _d[1] != -9999
        # Our cleaned up arrays containing the radii and burning values
        r, v = _d[0][_mask], _d[1][_mask] # Now you have data you can interpolate f = interp1d(r, v, kind='cubic')
        
        T_index.append(start_ind)
        R_star.append(r[-1]) # The last element is the radius of the star at time T_evo
        
        data_values.append([r, v])




    return data_values, T_index, R_star  # The lenghth can be gotten with time index. Every element is an array of r and burn values 
                        # that can be used to interpolate (f = interp1d(r, v, kind='cubic')



# ######################################################
# OPERATORS
# ######################################################
# This operator adds the geometry of one "piece" of the star
class OBJECT_OT_add_tulips3d_geo(bpy.types.Operator):
    """Operator to add Tulips3D geometry"""
    bl_idname = "object.tulips3d"
    bl_label = "Add Tulips3D Mesa Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.Tulips3DSettingsUI # We pull the current settings from context.scene.simple_geo_settings.

        if settings.type == 'ENERGY':
            
            data_values, T_index, R_star = prepare_energy_data(settings.mesaFilePath)
            
            make_star_pie(ob_name = settings.ob_name)

            obj = bpy.data.objects[settings.ob_name]

            # Fill out the CollectionProperty stellarProperties with data on the star
            obj.stellarProperties.clear() # Clear it just in case
            for _ in range(len(T_index)): obj.stellarProperties.add() # Create entries
            obj.stellarProperties.foreach_set("R_star", R_star) # Set data to the entries
            obj.stellarProperties.foreach_set("T_index", T_index)


            

        # # Choose which primitive to add
        # if settings.shape == 'CUBE':
        #     bpy.ops.mesh.primitive_cube_add(size=settings.size)
        # elif settings.shape == 'SPHERE':
        #     bpy.ops.mesh.primitive_uv_sphere_add(
        #         radius=settings.size,
        #         segments=settings.segments,
        #         ring_count=settings.segments // 2,
        #     )
        # elif settings.shape == 'CYLINDER':
        #     bpy.ops.mesh.primitive_cylinder_add(
        #         radius=settings.size,
        #         depth=settings.size * 2,
        #         vertices=settings.segments,
        #     )
        else:
            self.report({'ERROR'}, f"Unknown shape {settings.shape}")
            return {'CANCELLED'}

        return {'FINISHED'}


# ######################################################
# UI
# ######################################################

class Tulips3DSettingsUI(bpy.types.PropertyGroup):
    """Container for UI‑exposed settings"""

    type : EnumProperty(
        name="Type",
        description="What MESA data type to use",
        items=[
            ('ENERGY',   "Energy",   ""),
            ('NEXT',   "Which is next?",   ""),
        ],
        default='ENERGY',
    )

    ob_name : StringProperty(
        name="Object name",
        description="Name of the object in Blender",
        default="Star_Pie",
    )

    file_path_mesa_data = '/Users/vries001/Dropbox/0_DATA_BEN/PHYSICS/PROJECTS/tulips3D/example_MESA_data/single_11Msun/LOGS/'
    mesaFilePath : StringProperty(
        name="MESA Dir path",
        description="",
        default=file_path_mesa_data,
        subtype="DIR_PATH"
    )


    # shape : EnumProperty(
    #     name="Shape",
    #     description="What primitive to create",
    #     items=[
    #         ('CUBE',   "Cube",   ""),
    #         ('SPHERE', "UV Sphere", ""),
    #         ('CYLINDER',"Cylinder",""),
    #     ],
    #     default='CUBE',
    # )

    # size : FloatProperty(
    #     name="Size",
    #     description="Overall scale of the generated object",
    #     default=1.0,
    #     min=0.01,
    #     max=10.0,
    # )

    # segments : IntProperty(
    #     name="Segments",
    #     description="Resolution for sphere / cylinder",
    #     default=16,
    #     min=3,
    #     max=256,
    # )


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
        col.prop(settings, "type")
        col.prop(settings, "ob_name")
        col.prop(settings, "mesaFilePath")

        # col.prop(settings, "shape")
        # col.prop(settings, "size")
        # col.prop(settings, "segments")

        col.separator()
        col.operator("object.tulips3d", icon='MESH_CUBE')



# ######################################################
# DATA CLASSES - BLENDER
# ######################################################
class StellarEvolutionProperties(bpy.types.PropertyGroup): #FloatItem
    """Stellar evolution data saved on an object using a PropertyGroup"""
    R_star: FloatProperty(name="Value")
    T_index: FloatProperty(name="Value")
    #starName: StringProperty(name="starName")

# ######################################################
# DATA SYNC FUNCTIONS
# ######################################################
# def sync_StellarEvolutionProperties_to_attribute(obj, max_len=100):
#     # attr = obj.id_data.attributes.get("stellarProperties")
#     mesh = obj.data
#     attr = mesh.attributes.get("stellarProperties_R_star")

#     if not attr:
#         attr = mesh.attributes.new(name="stellarProperties_R_star",
#                                           type='FLOAT',
#                                           domain='POINT')
#     raw = [it.R_star for it in obj.stellarProperties]
#     padded = raw[:max_len] + [0.0] * (max_len - len(raw))
#     attr.data[0].value = padded

# ######################################################
# REGISTERING AND STUFF
# ######################################################
classes = (
    Tulips3DSettingsUI,
    OBJECT_OT_add_tulips3d_geo,
    VIEW3D_PT_tulips3d_panel,
    StellarEvolutionProperties
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Attach the PropertyGroup to the scene
    bpy.types.Scene.Tulips3DSettingsUI = bpy.props.PointerProperty(type=Tulips3DSettingsUI)

    # Attach an empty CollectionProperty to every Object
    bpy.types.Object.stellarProperties = CollectionProperty(
        type=StellarEvolutionProperties,
        name="Stellar evolution data",
        description="Stellar evolution properties (like t and R) as function of time"
    )

def unregister():
    # Remove the property first
    del bpy.types.Scene.Tulips3DSettingsUI
    del bpy.types.Object.stellarProperties

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()