bl_info = {
    "name": "UV Atlas Generator",
    "blender": (3, 6, 0),
    "category": "UV",
    "version": (1, 0, 0),
    "author": "GrizzlyOne95",
    "description": "Generate optimized UV atlas from Blender materials",
    "location": "View3D > Sidebar > UV Atlas",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "support": "COMMUNITY",
}

import bpy
import bmesh
import math
import mathutils
import numpy as np
from collections import defaultdict
from bpy.props import IntProperty, BoolProperty, EnumProperty
from bpy.types import Operator, Panel, PropertyGroup

class UVAtlasSettings(PropertyGroup):
    """Settings for UV Atlas Generator"""
    
    # === ATLAS SIZE SETTINGS ===
    max_atlas_size: IntProperty(
        name="Max Atlas Size",
        description="Maximum atlas texture size",
        default=2048,
        min=256,
        max=8192,
        step=1
    )
    
    force_square: BoolProperty(
        name="Force Square Atlas",
        description="Force atlas to be square (power of 2)",
        default=True
    )
    
    allow_non_power_of_2: BoolProperty(
        name="Allow Non-Power-of-2",
        description="Allow atlas sizes that aren't powers of 2",
        default=False
    )
    
    # === TEXTURE PROCESSING ===
    mirror_detection_mode: EnumProperty(
        name="Mirror Detection",
        description="How to handle mirrored UV faces",
        items=[
            ('AUTO', "Auto Detect", "Automatically detect mirrored faces by UV winding"),
            ('FORCE_REGULAR', "Force Regular", "Treat all faces as regular (no mirroring)"),
            ('FORCE_MIRRORED', "Force Mirrored", "Treat all faces as mirrored"),
            ('MANUAL', "Manual Selection", "Use manual flip settings below"),
        ],
        default='AUTO'
    )
    
    force_flip_u: BoolProperty(
        name="Force Flip U",
        description="Force horizontal flip for all textures",
        default=False
    )
    
    force_flip_v: BoolProperty(
        name="Force Flip V", 
        description="Force vertical flip for all textures",
        default=False
    )
    
    texture_wrap_mode: EnumProperty(
        name="Texture Wrap Mode",
        description="How to handle UV coordinates outside 0-1 range",
        items=[
            ('REPEAT', "Repeat", "Repeat texture (tiling)"),
            ('CLAMP', "Clamp", "Clamp to edge pixels"),
        ],
        default='REPEAT'
    )
    
    normalize_uv_ranges: BoolProperty(
        name="Normalize UV Ranges",
        description="Normalize UV coordinates to 0-1 range before processing",
        default=False
    )
    
    # === REGION SETTINGS ===
    target_region_size: IntProperty(
        name="Target Region Size",
        description="Target size for texture regions",
        default=256,
        min=16,
        max=1024
    )
    
    maintain_aspect_ratio: BoolProperty(
        name="Maintain Aspect Ratio",
        description="Keep original aspect ratio of texture regions",
        default=True
    )
    
    min_region_size: IntProperty(
        name="Min Region Size",
        description="Minimum size for texture regions",
        default=16,
        min=4,
        max=256
    )
    
    # === PACKING SETTINGS ===
    padding: IntProperty(
        name="Padding",
        description="Padding between texture regions in pixels",
        default=2,
        min=0,
        max=16
    )
    
    packing_algorithm: EnumProperty(
        name="Packing Algorithm",
        description="Algorithm for packing texture regions",
        items=[
            ('SIMPLE', "Simple Rows", "Pack in simple rows (fastest)"),
            ('SIZE_SORTED', "Size Sorted", "Sort by size before packing"),
            ('BEST_FIT', "Best Fit", "Try to minimize wasted space"),
        ],
        default='SIZE_SORTED'
    )
    
    allow_region_rotation: BoolProperty(
        name="Allow Rotation", 
        description="Allow rotating regions 90° for better packing",
        default=False
    )
    
    # === UV PROCESSING ===
    merge_identical_uvs: BoolProperty(
        name="Merge Identical UVs",
        description="Merge faces with identical UV layouts to save space",
        default=True
    )
    
    uv_precision: IntProperty(
        name="UV Precision",
        description="Decimal places for UV coordinate precision",
        default=4,
        min=2,
        max=8
    )
    
    # === OUTPUT SETTINGS ===
    atlas_name: bpy.props.StringProperty(
        name="Atlas Name",
        description="Name for the generated atlas texture",
        default="Atlas"
    )
    
    atlas_name_handling: EnumProperty(
        name="Name Conflict",
        description="How to handle existing images with the same name",
        items=[
            ('OVERWRITE', "Overwrite", "Replace existing image with same name"),
            ('CREATE_NEW', "Create New", "Create new image with unique name (append number)"),
            ('USE_EXISTING', "Use Existing", "Use existing image if it exists"),
        ],
        default='CREATE_NEW'
    )
    
    save_atlas_file: BoolProperty(
        name="Save Atlas File",
        description="Save atlas as image file to project directory",
        default=True
    )
    
    atlas_format: EnumProperty(
        name="Atlas Format",
        description="File format for saved atlas",
        items=[
            ('PNG', "PNG", "PNG format (lossless)"),
            ('JPEG', "JPEG", "JPEG format (lossy)"),
            ('TIFF', "TIFF", "TIFF format (lossless)"),
            ('EXR', "EXR", "OpenEXR format (HDR)"),
        ],
        default='PNG'
    )
    
    # === MATERIAL SETTINGS ===
    create_new_material: BoolProperty(
        name="Create New Material",
        description="Create new atlas material and assign to object",
        default=True
    )
    
    preserve_original_materials: BoolProperty(
        name="Preserve Originals",
        description="Keep original materials (don't replace them)",
        default=False
    )
    
    material_name: bpy.props.StringProperty(
        name="Material Name",
        description="Name for the atlas material",
        default="AtlasMaterial"
    )
    
    # === DEBUG & ADVANCED ===
    debug_mode: BoolProperty(
        name="Debug Mode",
        description="Print debug information to console",
        default=True
    )
    
    show_advanced_options: BoolProperty(
        name="Show Advanced Options",
        description="Show advanced configuration options",
        default=False
    )
    
    create_debug_materials: BoolProperty(
        name="Debug Materials",
        description="Create colored materials to visualize different regions",
        default=False
    )

class UV_ATLAS_OT_preset(Operator):
    """Apply UV Atlas Preset Settings"""
    bl_idname = "uv.atlas_preset"
    bl_label = "Apply Preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    preset: bpy.props.StringProperty()
    
    def execute(self, context):
        settings = context.scene.uv_atlas_settings
        
        if self.preset == 'GAME':
            # Game-ready settings: balanced quality/performance
            settings.max_atlas_size = 2048
            settings.target_region_size = 256
            settings.padding = 2
            settings.packing_algorithm = 'SIZE_SORTED'
            settings.mirror_detection_mode = 'AUTO'
            settings.texture_wrap_mode = 'REPEAT'
            settings.maintain_aspect_ratio = True
            settings.merge_identical_uvs = True
            settings.atlas_name_handling = 'CREATE_NEW'
            
        elif self.preset == 'HIGH_QUALITY':
            # High quality settings: maximum detail
            settings.max_atlas_size = 4096
            settings.target_region_size = 512
            settings.padding = 4
            settings.packing_algorithm = 'BEST_FIT'
            settings.mirror_detection_mode = 'AUTO'
            settings.texture_wrap_mode = 'REPEAT'
            settings.maintain_aspect_ratio = True
            settings.merge_identical_uvs = True
            settings.allow_region_rotation = True
            settings.atlas_name_handling = 'CREATE_NEW'
            
        elif self.preset == 'MOBILE':
            # Mobile-optimized settings: small sizes
            settings.max_atlas_size = 1024
            settings.target_region_size = 128
            settings.padding = 1
            settings.packing_algorithm = 'SIMPLE'
            settings.mirror_detection_mode = 'AUTO'
            settings.texture_wrap_mode = 'CLAMP'
            settings.maintain_aspect_ratio = False
            settings.merge_identical_uvs = True
            settings.atlas_name_handling = 'OVERWRITE'
            
        elif self.preset == 'CUSTOM':
            # Reset to defaults for custom configuration
            settings.max_atlas_size = 2048
            settings.target_region_size = 256
            settings.padding = 2
            settings.packing_algorithm = 'SIZE_SORTED'
            settings.mirror_detection_mode = 'AUTO'
            settings.show_advanced_options = True
            settings.atlas_name_handling = 'CREATE_NEW'
        
        self.report({'INFO'}, f"Applied {self.preset} preset")
        return {'FINISHED'}


class UV_ATLAS_OT_generate(Operator):
    """Generate UV Atlas with Mirror Support"""
    bl_idname = "uv.generate_atlas"
    bl_label = "Generate UV Atlas"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None and 
                context.object.type == 'MESH' and
                context.object.mode == 'OBJECT')
    
    def execute(self, context):
        settings = context.scene.uv_atlas_settings
        
        try:
            self.generate_atlas(context, settings)
            self.report({'INFO'}, "UV Atlas generated successfully!")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error generating atlas: {str(e)}")
            return {'CANCELLED'}
    
    def generate_atlas(self, context, settings):
        """Main atlas generation function"""
        obj = context.object
        
        if not obj or obj.type != 'MESH':
            raise Exception("No mesh object selected")
        
        if not obj.data.materials:
            raise Exception("Object has no materials")
        
        mesh = obj.data
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            uv_layer = bm.loops.layers.uv.verify()
            bm.faces.ensure_lookup_table()
            
            if settings.debug_mode:
                print(f"Processing mesh: {obj.name}")
                print(f"Faces: {len(bm.faces)}, Materials: {len(obj.data.materials)}")
            
            # Group faces by image and detect mirroring needs
            material_groups = self.group_faces_by_material(bm, obj, uv_layer, settings)
            
            if not material_groups:
                raise Exception("No valid materials with textures found")
            
            if settings.debug_mode:
                print(f"Found {len(material_groups)} unique textures")
            
            # Create texture regions
            total_regions = self.create_texture_regions(material_groups, settings, uv_layer)
            
            if not total_regions:
                raise Exception("No texture regions created")
            
            # Calculate optimal atlas size
            atlas_size = self.calculate_atlas_size(total_regions, settings)
            
            if settings.debug_mode:
                if isinstance(atlas_size, tuple):
                    print(f"Using atlas size: {atlas_size[0]}x{atlas_size[1]}")
                else:
                    print(f"Using atlas size: {atlas_size}x{atlas_size}")
            
            # Build the atlas
            atlas_image, atlas_regions = self.build_atlas(total_regions, atlas_size, settings)
            
            # Handle both square and rectangular atlas sizes
            if isinstance(atlas_size, tuple):
                atlas_width, atlas_height = atlas_size
            else:
                atlas_width = atlas_height = atlas_size
            
            # Remap UVs
            self.remap_uvs(atlas_regions, bm, uv_layer, atlas_width, atlas_height)
            
            # Create new material
            if settings.create_new_material:
                # Create simple atlas material
                mat = bpy.data.materials.new(name=settings.material_name)
                mat.use_nodes = True
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                tex_node.image = atlas_image
                mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_node.outputs['Color'])
                
                # Replace all materials with atlas material
                obj.data.materials.clear()
                obj.data.materials.append(mat)
                for face in bm.faces:
                    face.material_index = 0
            
            # Update mesh
            bm.to_mesh(mesh)
            
            efficiency = (sum(r['width'] * r['height'] for r in total_regions) / (atlas_width * atlas_height)) * 100
            
            if settings.debug_mode:
                print(f"✅ Optimized atlas complete!")
                print(f"📊 Final atlas size: {atlas_width}x{atlas_height}")
                print(f"📦 Total regions packed: {len(total_regions)}")
                print(f"📈 Atlas efficiency: {efficiency:.1f}%")
                
        except Exception as e:
            if bm.is_valid:
                bm.free()
            raise e
        finally:
            if bm.is_valid:
                bm.free()
    
    def is_face_uv_mirrored(self, face, uv_layer):
        """Check if face has mirrored UV coordinates (negative winding)"""
        uvs = [loop[uv_layer].uv for loop in face.loops]
        if len(uvs) < 3:
            return False
        # Calculate signed area using cross product
        v0, v1, v2 = uvs[0], uvs[1], uvs[2]
        cross = (v1 - v0).cross(v2 - v0)
        return cross < 0
    
    def sample_texture(self, src_pixels, u, v, width, height, wrap_mode='REPEAT'):
        """Sample texture with proper wrapping"""
        if wrap_mode == 'REPEAT':
            u = u % 1.0
            v = v % 1.0
        elif wrap_mode == 'CLAMP':
            u = max(0.0, min(1.0, u))
            v = max(0.0, min(1.0, v))

        x = int(u * width)
        y = int(v * height)
        x = max(0, min(width - 1, x))
        y = max(0, min(height - 1, y))
        return src_pixels[y, x]
    
    def group_faces_by_material(self, bm, obj, uv_layer, settings):
        """Group faces by image and detect mirroring needs"""
        material_groups = defaultdict(lambda: {'regular': [], 'mirrored': []})
        
        for face in bm.faces:
            mat_idx = face.material_index
            mat = obj.data.materials[mat_idx] if mat_idx < len(obj.data.materials) else None
            if not mat or not mat.use_nodes:
                continue
            
            img_nodes = [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE']
            if not img_nodes:
                continue
            
            img = img_nodes[0].image
            if not img or not img.has_data:
                continue
            
            face_data = {
                'face': face,
                'image': img,
                'material': mat,
                'face_index': face.index
            }
            
            # Determine if this face should be mirrored based on settings
            should_mirror = False
            
            if settings.mirror_detection_mode == 'AUTO':
                should_mirror = self.is_face_uv_mirrored(face, uv_layer)
            elif settings.mirror_detection_mode == 'FORCE_MIRRORED':
                should_mirror = True
            elif settings.mirror_detection_mode == 'FORCE_REGULAR':
                should_mirror = False
            elif settings.mirror_detection_mode == 'MANUAL':
                # In manual mode, we'll handle flipping at the texture level
                # Don't use mirrored grouping for manual mode
                should_mirror = False
            
            if should_mirror:
                material_groups[img.name]['mirrored'].append(face_data)
            else:
                material_groups[img.name]['regular'].append(face_data)
        
        return material_groups
    
    def compute_uv_bounds(self, face_group, uv_layer):
        """Compute UV bounds for a group of faces"""
        all_uvs = []
        for item in face_group:
            face_uvs = [loop[uv_layer].uv.copy() for loop in item['face'].loops]
            all_uvs.extend(face_uvs)
        
        if not all_uvs:
            return 0, 1, 0, 1
        
        u_coords = [uv.x for uv in all_uvs]
        v_coords = [uv.y for uv in all_uvs]
        return min(u_coords), max(u_coords), min(v_coords), max(v_coords)
    
    def create_region_texture(self, src_pixels, img_size, u_min, u_max, v_min, v_max, settings, region_type='regular'):
        """Create a texture region with proper scaling and settings"""
        u_range = u_max - u_min
        v_range = v_max - v_min
        
        # Determine flip settings based on mode and region type
        flip_u = False
        flip_v = False
        
        if settings.mirror_detection_mode == 'MANUAL':
            # In manual mode, apply user-specified flips to all regions
            flip_u = settings.force_flip_u
            flip_v = settings.force_flip_v
        elif region_type == 'mirrored':
            # For auto-detected mirrored regions, flip U only
            flip_u = True
            flip_v = False
        
        if settings.debug_mode:
            print(f"Region {region_type}: flip_u={flip_u}, flip_v={flip_v}")
        
        # Calculate region size based on UV coverage and source image size
        if settings.maintain_aspect_ratio:
            base_w = max(settings.min_region_size, math.ceil(abs(u_range) * img_size[0]))
            base_h = max(settings.min_region_size, math.ceil(abs(v_range) * img_size[1]))
            
            # Scale down if too large, but maintain aspect ratio
            scale = min(settings.target_region_size / max(base_w, base_h), 1.0)
            region_w = max(settings.min_region_size, int(base_w * scale))
            region_h = max(settings.min_region_size, int(base_h * scale))
        else:
            # Force to target size, ignoring aspect ratio
            region_w = settings.target_region_size
            region_h = settings.target_region_size
        
        region_pixels = np.zeros((region_h, region_w, 4), dtype=np.float32)
        
        for row in range(region_h):
            for col in range(region_w):
                u_norm = col / max(1, region_w - 1)
                v_norm = row / max(1, region_h - 1)

                if flip_u: 
                    u_norm = 1.0 - u_norm
                if flip_v: 
                    v_norm = 1.0 - v_norm

                src_u = u_min + u_norm * u_range
                src_v = v_min + v_norm * v_range

                region_pixels[row, col] = self.sample_texture(
                    src_pixels, src_u, src_v, img_size[0], img_size[1], 
                    wrap_mode=settings.texture_wrap_mode
                )
        
        return region_pixels, region_w, region_h
    
    def create_texture_regions(self, material_groups, settings, uv_layer):
        """Create texture regions for all materials"""
        total_regions = []
        
        for img_name, groups in material_groups.items():
            if not groups['regular'] and not groups['mirrored']:
                continue
            
            img = (groups['regular'] + groups['mirrored'])[0]['image']
            src_pixels = np.array(img.pixels[:]).reshape((img.size[1], img.size[0], 4))
            
            # Process regular faces
            if groups['regular']:
                u_min, u_max, v_min, v_max = self.compute_uv_bounds(groups['regular'], uv_layer)
                region_pixels, region_w, region_h = self.create_region_texture(
                    src_pixels, img.size, u_min, u_max, v_min, v_max, settings, region_type='regular'
                )
                
                region_info = {
                    'type': 'regular',
                    'img_name': img_name,
                    'pixels': region_pixels,
                    'width': region_w,
                    'height': region_h,
                    'u_min': u_min, 'u_max': u_max,
                    'v_min': v_min, 'v_max': v_max,
                    'faces': groups['regular']
                }
                total_regions.append(region_info)
            
            # Process mirrored faces (horizontally flipped)
            if groups['mirrored']:
                u_min, u_max, v_min, v_max = self.compute_uv_bounds(groups['mirrored'], uv_layer)
                region_pixels, region_w, region_h = self.create_region_texture(
                    src_pixels, img.size, u_min, u_max, v_min, v_max, settings, region_type='mirrored'
                )
                
                region_info = {
                    'type': 'mirrored',
                    'img_name': img_name,
                    'pixels': region_pixels,
                    'width': region_w,
                    'height': region_h,
                    'u_min': u_min, 'u_max': u_max,
                    'v_min': v_min, 'v_max': v_max,
                    'faces': groups['mirrored']
                }
                total_regions.append(region_info)
        
        return total_regions
    
    def calculate_atlas_size(self, regions, settings):
        """Calculate minimum atlas size needed for all regions"""
        total_area = sum(r['width'] * r['height'] for r in regions)
        
        # Add padding area
        padding_area = len(regions) * settings.padding * settings.padding * 4
        total_area += padding_area
        
        # Start with square root and find next power of 2
        min_size = int(math.sqrt(total_area))
        
        if settings.allow_non_power_of_2:
            # Allow any size, start from minimum
            atlas_size = max(64, min_size)
            while atlas_size <= settings.max_atlas_size:
                if self.test_packing(regions, atlas_size, settings.padding):
                    break
                atlas_size += 64  # Increment by 64
        else:
            # Force power of 2
            atlas_size = 64
            while atlas_size < min_size and atlas_size < settings.max_atlas_size:
                atlas_size *= 2
            
            # Test if regions actually fit
            while atlas_size <= settings.max_atlas_size:
                if self.test_packing(regions, atlas_size, settings.padding):
                    break
                atlas_size *= 2
        
        if not settings.force_square and settings.allow_non_power_of_2:
            # Try rectangular layouts for better efficiency
            for width in range(atlas_size, settings.max_atlas_size + 1, 64):
                for height in range(atlas_size, settings.max_atlas_size + 1, 64):
                    if width * height < atlas_size * atlas_size:
                        continue
                    if self.test_packing_rectangular(regions, width, height, settings.padding):
                        return (width, height)
        
        return atlas_size if isinstance(atlas_size, int) else min(atlas_size, settings.max_atlas_size)
    
    def resolve_atlas_name(self, base_name, atlas_width, atlas_height, settings):
        """Resolve atlas name conflicts based on user settings"""
        existing_image = bpy.data.images.get(base_name)
        
        if not existing_image:
            # No conflict, use the base name
            return base_name
        
        if settings.atlas_name_handling == 'OVERWRITE':
            # Remove existing image and use the same name
            if settings.debug_mode:
                print(f"🗑️ Removing existing image: {base_name}")
            bpy.data.images.remove(existing_image)
            return base_name
            
        elif settings.atlas_name_handling == 'USE_EXISTING':
            # Check if existing image has compatible dimensions
            if (existing_image.size[0] == atlas_width and 
                existing_image.size[1] == atlas_height):
                if settings.debug_mode:
                    print(f"♻️ Reusing existing image: {base_name}")
                return base_name
            else:
                if settings.debug_mode:
                    print(f"⚠️ Existing image {base_name} has wrong size ({existing_image.size[0]}x{existing_image.size[1]} vs {atlas_width}x{atlas_height}), creating new")
                # Fall back to creating new with unique name
                return self.generate_unique_name(base_name)
                
        elif settings.atlas_name_handling == 'CREATE_NEW':
            # Generate a unique name
            return self.generate_unique_name(base_name)
        
        return base_name
    
    def generate_unique_name(self, base_name):
        """Generate a unique name by appending numbers"""
        if not bpy.data.images.get(base_name):
            return base_name
        
        counter = 1
        while True:
            new_name = f"{base_name}.{counter:03d}"
            if not bpy.data.images.get(new_name):
                return new_name
            counter += 1
            if counter > 999:  # Safety limit
                import time
                timestamp = int(time.time()) % 10000
                return f"{base_name}_{timestamp}"
    
    def test_packing_rectangular(self, regions, width, height, padding):
        """Test if regions can fit in a rectangular atlas"""
        offset_x = padding
        offset_y = padding
        row_height = 0
        
        for region in regions:
            if offset_x + region['width'] + padding > width:
                offset_x = padding
                offset_y += row_height + padding
                row_height = 0
            
            if offset_y + region['height'] + padding > height:
                return False
            
            offset_x += region['width'] + padding
            row_height = max(row_height, region['height'])
        
        return True
    
    def test_packing(self, regions, atlas_size, padding):
        """Test if regions can fit in the given atlas size"""
        offset_x = padding
        offset_y = padding
        row_height = 0
        
        for region in regions:
            if offset_x + region['width'] + padding > atlas_size:
                offset_x = padding
                offset_y += row_height + padding
                row_height = 0
            
            if offset_y + region['height'] + padding > atlas_size:
                return False
            
            offset_x += region['width'] + padding
            row_height = max(row_height, region['height'])
        
        return True
    
    def build_atlas(self, total_regions, atlas_size, settings):
        """Build the atlas texture"""
        # Handle both square and rectangular atlas sizes
        if isinstance(atlas_size, tuple):
            atlas_width, atlas_height = atlas_size
        else:
            atlas_width = atlas_height = atlas_size
        
        # Sort regions based on packing algorithm
        if settings.packing_algorithm == 'SIZE_SORTED':
            total_regions.sort(key=lambda r: r['width'] * r['height'], reverse=True)
        elif settings.packing_algorithm == 'BEST_FIT':
            total_regions.sort(key=lambda r: max(r['width'], r['height']), reverse=True)
        
        # Handle atlas image naming and conflicts
        final_atlas_name = self.resolve_atlas_name(settings.atlas_name, atlas_width, atlas_height, settings)
        
        atlas_image = bpy.data.images.new(final_atlas_name, width=atlas_width, height=atlas_height)
        atlas_pixels = np.zeros((atlas_height, atlas_width, 4), dtype=np.float32)
        atlas_regions = {}
        
        offset_x = settings.padding
        offset_y = settings.padding
        row_height = 0
        
        for region in total_regions:
            # Check if we need to move to next row
            if offset_x + region['width'] + settings.padding > atlas_width:
                offset_x = settings.padding
                offset_y += row_height + settings.padding
                row_height = 0
            
            # For best fit packing, try rotating region if it helps
            rotated = False
            if (settings.packing_algorithm == 'BEST_FIT' and 
                settings.allow_region_rotation and
                offset_x + region['height'] + settings.padding <= atlas_width and
                offset_y + region['width'] + settings.padding <= atlas_height and
                region['width'] > region['height']):
                # Rotate region 90 degrees
                region['pixels'] = np.rot90(region['pixels'])
                region['width'], region['height'] = region['height'], region['width']
                rotated = True
            
            # Copy region pixels to atlas
            for row in range(region['height']):
                for col in range(region['width']):
                    atlas_x = offset_x + col
                    atlas_y = offset_y + row
                    if atlas_x < atlas_width and atlas_y < atlas_height:
                        atlas_pixels[atlas_y, atlas_x] = region['pixels'][row, col]
            
            # Store region info for UV remapping
            region_key = f"{region['img_name']}_{region['type']}"
            atlas_regions[region_key] = {
                'atlas_x': offset_x, 'atlas_y': offset_y,
                'width': region['width'], 'height': region['height'],
                'u_min': region['u_min'], 'u_max': region['u_max'],
                'v_min': region['v_min'], 'v_max': region['v_max'],
                'faces': region['faces'],
                'type': region['type'],
                'rotated': rotated
            }
            
            offset_x += region['width'] + settings.padding
            row_height = max(row_height, region['height'])
        
        # Write pixels to Blender image
        atlas_image.pixels = atlas_pixels.flatten().tolist()
        
        # Save atlas file if requested
        if settings.save_atlas_file:
            atlas_image.filepath_raw = f"//{final_atlas_name}.{settings.atlas_format.lower()}"
            atlas_image.file_format = settings.atlas_format
            atlas_image.save()
        
        if settings.debug_mode:
            print(f"📁 Created atlas image: {final_atlas_name}")
        
        return atlas_image, atlas_regions
    
    def remap_uvs(self, atlas_regions, bm, uv_layer, atlas_width, atlas_height):
        """Remap UVs to atlas coordinates"""
        for region_key, region in atlas_regions.items():
            for item in region['faces']:
                face = item['face']
                for loop in face.loops:
                    old_uv = loop[uv_layer].uv
                    
                    # Calculate normalized coordinates within the original UV region
                    u_norm = (old_uv.x - region['u_min']) / max(0.001, region['u_max'] - region['u_min'])
                    v_norm = (old_uv.y - region['v_min']) / max(0.001, region['v_max'] - region['v_min'])
                    
                    # Handle rotation if region was rotated during packing
                    if region.get('rotated', False):
                        u_norm, v_norm = v_norm, 1.0 - u_norm
                    
                    # Handle mirrored UVs - flip the u coordinate since we flipped the texture
                    if region['type'] == 'mirrored':
                        u_norm = 1.0 - u_norm  # Flip u coordinate to match the flipped texture
                    
                    # Map to atlas coordinates
                    new_u = (region['atlas_x'] + u_norm * region['width']) / atlas_width
                    new_v = (region['atlas_y'] + v_norm * region['height']) / atlas_height
                    
                    loop[uv_layer].uv = (new_u, new_v)
    
    def create_atlas_material(self, obj, atlas_image):
        """Create new material with atlas texture"""
        mat = bpy.data.materials.new(name="AtlasMaterial")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex_node.image = atlas_image
        mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_node.outputs['Color'])
        
        # Replace all materials with atlas material
        obj.data.materials.clear()
        obj.data.materials.append(mat)


class UV_ATLAS_PT_panel(Panel):
    """UV Atlas Generator Panel"""
    bl_label = "UV Atlas Generator"
    bl_idname = "UV_ATLAS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UV Atlas"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.uv_atlas_settings
        
        # Object info
        obj = context.object
        if obj and obj.type == 'MESH':
            box = layout.box()
            box.label(text=f"Selected: {obj.name}", icon='OBJECT_DATA')
            box.label(text=f"Faces: {len(obj.data.polygons)}")
            box.label(text=f"Materials: {len(obj.data.materials)}")
        else:
            layout.label(text="Select a mesh object", icon='ERROR')
            return
        
        # === OUTPUT CONTROL ===
        layout.separator()
        layout.label(text="Output Control:", icon='FILE_IMAGE')
        
        col = layout.column(align=True)
        col.prop(settings, "atlas_name")
        col.prop(settings, "atlas_name_handling")
        
        # Show info about name handling
        existing_img = bpy.data.images.get(settings.atlas_name)
        if existing_img:
            box = layout.box()
            if settings.atlas_name_handling == 'OVERWRITE':
                box.label(text=f"⚠️ Will overwrite existing '{settings.atlas_name}'", icon='ERROR')
            elif settings.atlas_name_handling == 'CREATE_NEW':
                box.label(text=f"📝 Will create new name (e.g. '{settings.atlas_name}.001')", icon='INFO')
            elif settings.atlas_name_handling == 'USE_EXISTING':
                box.label(text=f"♻️ Will reuse existing '{settings.atlas_name}' if compatible", icon='INFO')
        
        col.prop(settings, "save_atlas_file")
        if settings.save_atlas_file:
            col.prop(settings, "atlas_format")
        
        # === ATLAS SIZE SETTINGS ===
        layout.separator()
        layout.label(text="Atlas Settings:", icon='IMAGE_DATA')
        
        col = layout.column(align=True)
        col.prop(settings, "max_atlas_size")
        
        row = col.row(align=True)
        row.prop(settings, "force_square")
        row.prop(settings, "allow_non_power_of_2")
        
        # === TEXTURE PROCESSING ===
        layout.separator()
        layout.label(text="Texture Processing:", icon='TEXTURE')
        
        col = layout.column(align=True)
        col.prop(settings, "mirror_detection_mode")
        
        # Show manual flip options if manual mode selected
        if settings.mirror_detection_mode == 'MANUAL':
            row = col.row(align=True)
            row.prop(settings, "force_flip_u")
            row.prop(settings, "force_flip_v")
        
        col.prop(settings, "texture_wrap_mode")
        
        # === REGION SETTINGS ===
        layout.separator()
        layout.label(text="Region Settings:", icon='UV')
        
        col = layout.column(align=True)
        col.prop(settings, "target_region_size")
        col.prop(settings, "min_region_size")
        col.prop(settings, "maintain_aspect_ratio")
        
        # === PACKING SETTINGS ===
        layout.separator()
        layout.label(text="Packing:", icon='PACKAGE')
        
        col = layout.column(align=True)
        col.prop(settings, "packing_algorithm")
        col.prop(settings, "padding")
        if settings.packing_algorithm == 'BEST_FIT':
            col.prop(settings, "allow_region_rotation")
        
        # === ADVANCED OPTIONS ===
        layout.separator()
        row = layout.row()
        row.prop(settings, "show_advanced_options", icon='TRIA_DOWN' if settings.show_advanced_options else 'TRIA_RIGHT')
        
        if settings.show_advanced_options:
            box = layout.box()
            
            # UV Processing
            box.label(text="UV Processing:", icon='UV_DATA')
            col = box.column(align=True)
            col.prop(settings, "normalize_uv_ranges")
            col.prop(settings, "merge_identical_uvs")
            col.prop(settings, "uv_precision")
            
            # Output Settings
            box.label(text="Output:", icon='EXPORT')
            col = box.column(align=True)
            col.prop(settings, "atlas_name")
            col.prop(settings, "atlas_name_handling")
            col.prop(settings, "save_atlas_file")
            if settings.save_atlas_file:
                col.prop(settings, "atlas_format")
            
            # Material Settings
            box.label(text="Materials:", icon='MATERIAL')
            col = box.column(align=True)
            col.prop(settings, "create_new_material")
            if settings.create_new_material:
                col.prop(settings, "material_name")
                col.prop(settings, "preserve_original_materials")
            
            # Debug Settings
            box.label(text="Debug:", icon='CONSOLE')
            col = box.column(align=True)
            col.prop(settings, "debug_mode")
            col.prop(settings, "create_debug_materials")
        
        # === GENERATE BUTTON ===
        layout.separator()
        
        # Check if object is valid
        if obj and obj.type == 'MESH' and obj.mode == 'OBJECT':
            op = layout.operator("uv.generate_atlas", icon='PLAY', text="Generate UV Atlas")
        else:
            layout.label(text="Switch to Object mode", icon='INFO')
        
        # === QUICK PRESETS ===
        if not settings.show_advanced_options:
            layout.separator()
            box = layout.box()
            box.label(text="Quick Presets:", icon='PRESET')
            
            row = box.row(align=True)
            row.operator("uv.atlas_preset", text="Game Ready").preset = 'GAME'
            row.operator("uv.atlas_preset", text="High Quality").preset = 'HIGH_QUALITY'
            
            row = box.row(align=True)
            row.operator("uv.atlas_preset", text="Mobile").preset = 'MOBILE'
            row.operator("uv.atlas_preset", text="Custom").preset = 'CUSTOM'


# Registration
classes = (
    UVAtlasSettings,
    UV_ATLAS_OT_preset,
    UV_ATLAS_OT_generate,
    UV_ATLAS_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.uv_atlas_settings = bpy.props.PointerProperty(type=UVAtlasSettings)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.uv_atlas_settings

if __name__ == "__main__":
    register()
