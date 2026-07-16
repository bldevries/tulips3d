
import bpy
import math
import os

# ######################################################
#
# ######################################################
def load_texture(texture_path):
    '''Loads a texture into an image'''
    
    if texture_path:
        if texture_path in bpy.data.images:
            img = bpy.data.images[texture_path]
            print("✓ Image loaded ", img)
        else:
            try:
                img = bpy.data.images.load(texture_path)
                # img.colorspace_settings.name = 'Non-Color'
                if hasattr(img, 'use_float'):
                    img.use_float = True
                print("✓ Image loaded ", img)
            except Exception as e:
                print(f"Warning: Could not load image: {e}")
                img = None
                return img
    return img

# ######################################################
#
# ######################################################
def add_geo_nodes(obj, radius_texture_path, teff_texture_path, nr_of_files=498, \
                    star_radius_attr_name = "StarRadiusAttribute",\
                    Teff_attr_name = "TeffAttribute"\
                    ):
    ''' Creates geometry nodes to scale the star and to save the Teff and the star radius
    as attributes to use in the shader nodes'''

    img_R = load_texture(radius_texture_path)
    img_Teff = load_texture(teff_texture_path)

    # === CREATE NODE GROUP & MODIFIER ===
    node_group_name = "NodeGroup"
    try:
        node_group = bpy.data.node_groups.new(name=node_group_name, type='GeometryNodeTree')
        print(f"✓ Created node group: '{node_group_name}'")
    except Exception as e:
        node_group = bpy.data.node_groups.get(node_group_name)
        if not node_group:
            print(f"Error creating node group: {e}")
            return None
        print(f"✓ Reused existing node group: '{node_group_name}'")
    
    # === SETUP MODIFIER ===
    mod_name = "mod_StoreRadiusStar"
    geom_mod = None
    for mod in obj.modifiers:
        if mod.type == 'NODES' and mod.name == mod_name:
            geom_mod = mod
            break
    
    if geom_mod is None:
        geom_mod = obj.modifiers.new(name=mod_name, type='NODES')
    
    geom_mod.node_group = node_group
    
    # === DEFINE INTERFACE ===
    if hasattr(node_group.interface, 'clear'):
        node_group.interface.clear()
    
    node_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    print("✓ Interface sockets defined")
    
    # Clear nodes
    for node in node_group.nodes:
        node_group.nodes.remove(node)
    node_group.links.clear()
    
    # IN/OUT NODES
    input_node = node_group.nodes.new('NodeGroupInput')
    input_node.location = (-200, 0)
    
    output_node = node_group.nodes.new('NodeGroupOutput')
    output_node.location = (1200, 0)

    # SCALE GEOMETRY
    frame_input_vector_node = node_group.nodes.new("FunctionNodeInputVector")
    frame_input_vector_node.location = (-1200, 0)
    dr = frame_input_vector_node.driver_add("vector", 0).driver #bpy.data.node_groups['NodeGroup.038'].nodes['Vector']
    var = dr.variables.new()
    var.name = "frame"
    var.targets[0].id_type = 'SCENE'
    var.targets[0].id = bpy.data.scenes[bpy.context.scene.name]
    var.targets[0].data_path = 'frame_current'
    dr.expression = 'frame'
    # This needs a driver input to set it to #frame
    # frame_input_vector_node.vector[0] = '#frame'

    scale_frame_vector_node = node_group.nodes.new("ShaderNodeVectorMath")
    scale_frame_vector_node.operation="SCALE"
    scale_frame_vector_node.location = (-1000, 0)
    #print([i.type for i in list(scale_frame_vector_node.inputs)])
    scale_frame_vector_node.inputs[3].default_value = 1./(nr_of_files+1) # Frame number starts at 1 #0.002
    # scale_frame_vector_node.location = (-800, -200)

    # Radius texture and image node
    radius_texture_node = node_group.nodes.new("GeometryNodeImageTexture")
    radius_texture_node.location = (-600,-400)
    image_node = node_group.nodes.new("GeometryNodeInputImage")
    image_node.location = (-1000,-400)
    image_node.image = img_R

    sep_radius_text_node = node_group.nodes.new("ShaderNodeSeparateXYZ")
    sep_radius_text_node.location = (-200, -400)

    combine_radius_text_node = node_group.nodes.new("ShaderNodeCombineXYZ")
    combine_radius_text_node.location = (0,-400)

    scale_transform_node = node_group.nodes.new("GeometryNodeTransform")
    scale_transform_node.location = (200,0)

    # Teff texture and image node
    Teff_texture_node = node_group.nodes.new("GeometryNodeImageTexture")
    Teff_texture_node.location = (400,300)
    image_node_Teff = node_group.nodes.new("GeometryNodeInputImage")
    image_node_Teff.location = (100,250)
    image_node_Teff.image = img_Teff

    links = node_group.links
    link_frameVector_scale = links.new(frame_input_vector_node.outputs[0], scale_frame_vector_node.inputs[0])
    link_scale_RscaleText = links.new(scale_frame_vector_node.outputs[0], radius_texture_node.inputs[1])
    link_scale_TeffText = links.new(scale_frame_vector_node.outputs[0], Teff_texture_node.inputs[1])
    link_image_RscaleText = links.new(image_node.outputs[0], radius_texture_node.inputs[0])
    link_image_TeffText = links.new(image_node_Teff.outputs[0], Teff_texture_node.inputs[0])
    link_RscaleText_sepXYZ = links.new(radius_texture_node.outputs[0], sep_radius_text_node.inputs[0])
    link_sepXYZ_combX = links.new(sep_radius_text_node.outputs[0], combine_radius_text_node.inputs[0])
    link_sepXYZ_combY = links.new(sep_radius_text_node.outputs[0], combine_radius_text_node.inputs[1])
    link_sepXYZ_combZ = links.new(sep_radius_text_node.outputs[0], combine_radius_text_node.inputs[2])
    link_sepXYZ_combZ = links.new(combine_radius_text_node.outputs[0], scale_transform_node.inputs[4])


    # SAVING THE STAR RADIUS AS ATTRIBUTE
    pos_node = node_group.nodes.new('GeometryNodeInputPosition')
    pos_node.location = (0, -600)

    length_node = node_group.nodes.new('ShaderNodeVectorMath')
    length_node.operation = "LENGTH"
    length_node.location = (200, -600)

    # Better: Create Attribute Statistic to get max distance, then Mix with 1.0
    stat_node = node_group.nodes.new('GeometryNodeAttributeStatistic')
    stat_node.location = (400, -300)
    stat_node.data_type = 'FLOAT'
    stat_node.domain = 'POINT'
    print("✓ Created Attribute Statistic node")

    store_node = node_group.nodes.new('GeometryNodeStoreNamedAttribute')
    store_node.location = (600, 0)
    store_node.data_type = 'FLOAT'
    store_node.domain = 'POINT'
    store_node.inputs[2].default_value = star_radius_attr_name
    # name_sock = find_socket(store_node.inputs, name='Name')
    
    store_Teff_node = node_group.nodes.new('GeometryNodeStoreNamedAttribute')
    store_Teff_node.location = (900, 0)
    store_Teff_node.data_type = 'FLOAT_COLOR'
    store_Teff_node.domain = 'POINT'
    store_Teff_node.inputs[2].default_value = Teff_attr_name

    # LINK THE NODES
    link_in_transform = links.new(input_node.outputs[0], scale_transform_node.inputs[0])
    
    link_in_store = links.new(scale_transform_node.outputs[0], store_node.inputs[0])

    link_storeR_storeTeff = links.new(store_node.outputs[0], store_Teff_node.inputs[0])

    link_store_out = links.new(store_Teff_node.outputs[0], output_node.inputs[0])

    link_input_stat = links.new(scale_transform_node.outputs[0], stat_node.inputs[0])
    
    # The math node is a bit tricky in its output sockets
    if length_node.outputs[0].type == "VALUE": i = 0
    else: i = 1
    link_pos_length = links.new(pos_node.outputs[0], length_node.inputs[0])
    link_length_stat = links.new(length_node.outputs[i], stat_node.inputs[2])
    
    link_stat_store = links.new(stat_node.outputs[4], store_node.inputs[3])
    link_Teff_storeTeff = links.new(Teff_texture_node.outputs[0], store_Teff_node.inputs[3])
    
# ######################################################
#
# ######################################################
def create_material_data_t_r(name, data_texture_path, nr_of_files=498):
    '''Creates a material with shader nodes to color the pie sides. Works
    for the regular data_t_r profile labels (like en, logT, etc)'''

    img = load_texture(data_texture_path)
    img.source = 'SEQUENCE'
    # img.auto_refresh = True

    mat = bpy.data.materials.new(name)
    mat.blend_method = 'BLEND' # Alpha Blend, Render polygon transparent, depending on alpha channel of the texture.
    mat.use_nodes = True
    mat.show_transparent_back = False
    nodes = mat.node_tree.nodes

    # clear all nodes to start clean
    nodes.clear()

    node_position = nodes.new(type="ShaderNodeTexCoord")
    #nodes.new(type='ShaderNodeNewGeometry')
    node_position.location = -2000, 150
    # bpy.ops.node.add_node(use_transform=True, type="ShaderNodeNewGeometry", visible_output="Position")

    # Length - R
    node_vec_length = nodes.new(type='ShaderNodeVectorMath')
    node_vec_length.operation = "LENGTH"
    node_vec_length.location = -1800, 150

    # GET THE THETA UV INDEX!
    # Sep XYZ
    sep_for_Z = nodes.new("ShaderNodeSeparateXYZ")
    sep_for_Z.location = (-1500, -200)

    # Div Z/R
    node_Z_div_R = nodes.new(type="ShaderNodeMath")
    node_Z_div_R.operation = "DIVIDE"
    node_Z_div_R.location = -1300, -200
    node_Z_div_R.inputs[1].default_value = 1

    # Arccos
    # bpy.ops.node.add_node(settings=[{"name":"operation", "value":"'ARCCOSINE'"}], use_transform=True, type="ShaderNodeMath")
    node_acos = nodes.new(type="ShaderNodeMath")
    node_acos.operation = "ARCCOSINE"
    node_acos.location = -1100, -200

    # divide pi
    node_div_pi = nodes.new(type="ShaderNodeMath")
    node_div_pi.operation = "DIVIDE"
    node_div_pi.location = -900, -200
    node_div_pi.inputs[1].default_value = math.pi
    # END: GET THE THETA UV INDEX!

    # Radius attribute
    node_maxRadius_attri = nodes.new(type='ShaderNodeAttribute')
    node_maxRadius_attri.attribute_name = "StarRadiusAttribute"
    node_maxRadius_attri.location = -1100, 0

    # Divide length/max
    node_divide = nodes.new(type="ShaderNodeMath")
    node_divide.operation = "DIVIDE"
    node_divide.location = -900, 150
    node_divide.inputs[1].default_value = 10

    # CombineXYZ
    node_XYZ = nodes.new(type="ShaderNodeCombineXYZ")
    node_XYZ.location = -700, 150
    

    # ImageTexture
    node_ShaderNodeTexImage = nodes.new(type='ShaderNodeTexImage')
    node_ShaderNodeTexImage.location = -500, 150
    node_ShaderNodeTexImage.image = img 
    node_ShaderNodeTexImage.extension = 'CLIP'
    node_ShaderNodeTexImage.image_user.frame_duration = nr_of_files
    node_ShaderNodeTexImage.image_user.frame_start = 0
    node_ShaderNodeTexImage.image_user.frame_offset = 1
    node_ShaderNodeTexImage.image_user.use_auto_refresh = True

    for i in node_ShaderNodeTexImage.inputs:
        print(i, i.type)
    # bpy.ops.node.add_node(use_transform=True, type="ShaderNodeTexImage")

    # Emission Shader
    node_emission = nodes.new(type='ShaderNodeEmission')#ShaderNodeBsdfDiffuse')
    node_emission.inputs[1].default_value = 0.5
    node_emission.location = -100, 150

    # Output
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_output.location = 200, 150

    # # link nodes
    links = mat.node_tree.links
    link_position_length = links.new(node_position.outputs[3], node_vec_length.inputs[0])
    link_position_sepXYZ = links.new(node_position.outputs[3], sep_for_Z.inputs[0])

    # The math node is a bit tricky in its output sockets
    if node_vec_length.outputs[0].type == "VALUE": i = 0
    else: i = 1
    link_length_div = links.new(node_vec_length.outputs[i], node_divide.inputs[0])

    link_maxRadius_div = links.new(node_maxRadius_attri.outputs[2], node_divide.inputs[1])
    link_div_XYZ = links.new(node_divide.outputs[0], node_XYZ.inputs[0])

    link_sepXYZ_ZdivR = links.new(sep_for_Z.outputs[2], node_Z_div_R.inputs[0])
    link_length_ZdivR = links.new(node_vec_length.outputs[i], node_Z_div_R.inputs[1])
    link_ZdivR_arccos = links.new(node_Z_div_R.outputs[0], node_acos.inputs[0])
    link_arccos_divPi = links.new(node_acos.outputs[0], node_div_pi.inputs[0])

    link_theta_XYZ = links.new(node_div_pi.outputs[0], node_XYZ.inputs[1])

    link_XYZ_text = links.new(node_XYZ.outputs[0], node_ShaderNodeTexImage.inputs[0])
    link_text_emm = links.new(node_ShaderNodeTexImage.outputs[0], node_emission.inputs[0])
    link_emm_out = links.new(node_emission.outputs[0], node_output.inputs[0])
    return mat

# ######################################################
#
# ######################################################
def update_material(mat, data_texture_path):
    '''Updates a material with another texture file. Works for both data_t_r profile
    data as well as the chemical profiles'''
    nodes = mat.node_tree.nodes
    print(nodes)
    if 'Image Texture' in nodes:
        if os.path.isfile(data_texture_path):

            img = load_texture(data_texture_path)
            img.source = 'SEQUENCE'
            nodes['Image Texture'].image = img
            return True
    return False

# ######################################################
#
# ######################################################
def create_material_Teff(name, color_attr_name="TeffAttribute"):
    mat = bpy.data.materials.new(name)
    mat.blend_method = 'BLEND' # Alpha Blend, Render polygon transparent, depending on alpha channel of the texture.
    mat.use_nodes = True
    mat.show_transparent_back = False
    nodes = mat.node_tree.nodes

    # clear all nodes to start clean
    nodes.clear()

    node_ver_col = nodes.new(type="ShaderNodeVertexColor")
    node_ver_col.location = -300, 150
    node_ver_col.layer_name = color_attr_name


    # Emission Shader
    node_emission = nodes.new(type='ShaderNodeEmission')#ShaderNodeBsdfDiffuse')
    node_emission.inputs[1].default_value = 0.5
    node_emission.location = -100, 150

    # Output
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_output.location = 200, 150

    links = mat.node_tree.links

    link_emm_out = links.new(node_emission.outputs[0], node_output.inputs[0])
    link_vertexcol_emm = links.new(node_ver_col.outputs[0], node_emission.inputs[0])

    return mat

