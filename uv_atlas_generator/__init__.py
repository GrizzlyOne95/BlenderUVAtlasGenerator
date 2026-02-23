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
            ('SIMPLE', "Insertion Order", "MaxRects packing with original order"),
            ('SIZE_SORTED', "Size Sorted", "MaxRects packing, sorted by area"),
            ('BEST_FIT', "Best Fit", "MaxRects packing, sorted by long edge"),
        ],
        default='SIZE_SORTED'
    )
    
    allow_region_rotation: BoolProperty(
        name="Allow Rotation", 
        description="Allow rotating regions 90° for better packing",
        default=False
    )

    rotation_safe_only: BoolProperty(
        name="Rotation Safe Only",
        description="Only rotate regions with axis-aligned UVs",
        default=True
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

    output_dir: bpy.props.StringProperty(
        name="Output Directory",
        description="Directory to save atlas images (blank = blend file directory)",
        subtype='DIR_PATH',
        default=""
    )

    atlas_name_preset: EnumProperty(
        name="Name Preset",
        description="Preset for atlas naming",
        items=[
            ('ATLAS', "Atlas Only", "{atlas}"),
            ('OBJECT_ATLAS', "Object + Atlas", "{object}_{atlas}"),
            ('OBJECT_TIMESTAMP', "Object + Timestamp", "{object}_{timestamp}"),
            ('ATLAS_TIMESTAMP', "Atlas + Timestamp", "{atlas}_{timestamp}"),
            ('CUSTOM', "Custom Template", "{custom}"),
        ],
        default='OBJECT_ATLAS'
    )

    atlas_name_template: bpy.props.StringProperty(
        name="Name Template",
        description="Custom name template using {object}, {atlas}, {timestamp}",
        default="{object}_{atlas}"
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
        objs = [o for o in context.selected_objects if o.type == 'MESH']
        if not objs:
            raise Exception("No mesh objects selected")

        for obj in objs:
            if not obj.data.materials:
                raise Exception(f"Object has no materials: {obj.name}")

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
                    raise Exception(f"No valid materials with textures found on {obj.name}")
                
                if settings.debug_mode:
                    print(f"Found {len(material_groups)} unique textures")
                
                # Create texture regions
                total_regions = self.create_texture_regions(material_groups, settings, uv_layer)
                
                if not total_regions:
                    raise Exception(f"No texture regions created for {obj.name}")
                
                # Calculate optimal atlas size
                atlas_size = self.calculate_atlas_size(total_regions, settings)
                
                if settings.debug_mode:
                    if isinstance(atlas_size, tuple):
                        print(f"Using atlas size: {atlas_size[0]}x{atlas_size[1]}")
                    else:
                        print(f"Using atlas size: {atlas_size}x{atlas_size}")
                
                # Build the atlas
                atlas_image, atlas_regions = self.build_atlas(total_regions, atlas_size, settings, obj)
                
                # Handle both square and rectangular atlas sizes
                if isinstance(atlas_size, tuple):
                    atlas_width, atlas_height = atlas_size
                else:
                    atlas_width = atlas_height = atlas_size
                
                # Remap UVs
                self.remap_uvs(atlas_regions, bm, uv_layer, atlas_width, atlas_height, settings)
                
                # Create materials
                if settings.create_debug_materials:
                    self.apply_debug_materials(obj, bm, atlas_regions, settings)
                elif settings.create_new_material:
                    self.apply_atlas_material(obj, bm, atlas_image, settings)
                
                # Update mesh
                bm.to_mesh(mesh)
                
                efficiency = (sum(r['width'] * r['height'] for r in total_regions) / (atlas_width * atlas_height)) * 100
                
                if settings.debug_mode:
                    print(f"✅ Optimized atlas complete for {obj.name}!")
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
    
    def normalize_uv(self, uv, settings):
        """Normalize UVs to 0-1 range if enabled."""
        if not settings.normalize_uv_ranges:
            return uv.x, uv.y
        return uv.x % 1.0, uv.y % 1.0

    def compute_uv_bounds(self, face_group, uv_layer, settings):
        """Compute UV bounds for a group of faces"""
        all_uvs = []
        for item in face_group:
            for loop in item['face'].loops:
                u, v = self.normalize_uv(loop[uv_layer].uv, settings)
                all_uvs.append((u, v))
        
        if not all_uvs:
            return 0, 1, 0, 1
        
        u_coords = [uv[0] for uv in all_uvs]
        v_coords = [uv[1] for uv in all_uvs]
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
                u_min, u_max, v_min, v_max = self.compute_uv_bounds(groups['regular'], uv_layer, settings)
                allow_rotate = self.is_region_rotation_safe(groups['regular'], uv_layer) if settings.rotation_safe_only else True
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
                    'faces': groups['regular'],
                    'allow_rotate': allow_rotate
                }
                total_regions.append(region_info)
            
            # Process mirrored faces (horizontally flipped)
            if groups['mirrored']:
                u_min, u_max, v_min, v_max = self.compute_uv_bounds(groups['mirrored'], uv_layer, settings)
                allow_rotate = self.is_region_rotation_safe(groups['mirrored'], uv_layer) if settings.rotation_safe_only else True
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
                    'faces': groups['mirrored'],
                    'allow_rotate': allow_rotate
                }
                total_regions.append(region_info)
        
        if settings.merge_identical_uvs:
            total_regions = self.merge_identical_regions(total_regions, settings)

        return total_regions

    def merge_identical_regions(self, regions, settings):
        """Merge regions that share the same UV bounds and image."""
        merged = {}

        def q(v):
            return round(v, settings.uv_precision)

        for region in regions:
            key = (
                region['img_name'],
                region['type'],
                q(region['u_min']), q(region['u_max']),
                q(region['v_min']), q(region['v_max']),
                region['width'], region['height'],
            )
            existing = merged.get(key)
            if not existing:
                merged[key] = region
                continue
            existing['faces'].extend(region['faces'])

        return list(merged.values())
    
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
            fit = False
            while atlas_size <= settings.max_atlas_size:
                if self.test_packing(regions, atlas_size, settings.padding, allow_rotate=settings.allow_region_rotation):
                    fit = True
                    break
                atlas_size += 64  # Increment by 64
            if not fit:
                raise Exception("Regions do not fit within max atlas size")
        else:
            # Force power of 2
            atlas_size = 64
            while atlas_size < min_size and atlas_size < settings.max_atlas_size:
                atlas_size *= 2
            
            # Test if regions actually fit
            fit = False
            while atlas_size <= settings.max_atlas_size:
                if self.test_packing(regions, atlas_size, settings.padding, allow_rotate=settings.allow_region_rotation):
                    fit = True
                    break
                atlas_size *= 2
            if not fit:
                raise Exception("Regions do not fit within max atlas size")
        
        if not settings.force_square and settings.allow_non_power_of_2:
            # Try rectangular layouts for better efficiency
            for width in range(atlas_size, settings.max_atlas_size + 1, 64):
                for height in range(atlas_size, settings.max_atlas_size + 1, 64):
                    if width * height < atlas_size * atlas_size:
                        continue
                    if self.test_packing_rectangular(regions, width, height, settings.padding, allow_rotate=settings.allow_region_rotation):
                        return (width, height)
        
        return atlas_size if isinstance(atlas_size, int) else min(atlas_size, settings.max_atlas_size)
    
    def build_atlas_name(self, settings, obj):
        template = settings.atlas_name_template
        if settings.atlas_name_preset == 'ATLAS':
            template = "{atlas}"
        elif settings.atlas_name_preset == 'OBJECT_ATLAS':
            template = "{object}_{atlas}"
        elif settings.atlas_name_preset == 'OBJECT_TIMESTAMP':
            template = "{object}_{timestamp}"
        elif settings.atlas_name_preset == 'ATLAS_TIMESTAMP':
            template = "{atlas}_{timestamp}"
        elif settings.atlas_name_preset == 'CUSTOM':
            template = settings.atlas_name_template

        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        return template.format(
            object=obj.name if obj else "Object",
            atlas=settings.atlas_name,
            timestamp=timestamp
        )

    def get_or_create_atlas_image(self, settings, atlas_width, atlas_height, obj=None):
        """Create or reuse atlas image based on name handling settings."""
        base_name = self.build_atlas_name(settings, obj)
        existing_image = bpy.data.images.get(base_name)
        
        if existing_image:
            if settings.atlas_name_handling == 'OVERWRITE':
                if settings.debug_mode:
                    print(f"🗑️ Removing existing image: {base_name}")
                bpy.data.images.remove(existing_image)
                existing_image = None
            elif settings.atlas_name_handling == 'USE_EXISTING':
                if (existing_image.size[0] == atlas_width and 
                    existing_image.size[1] == atlas_height):
                    if settings.debug_mode:
                        print(f"♻️ Reusing existing image: {base_name}")
                    return existing_image, base_name
                if settings.debug_mode:
                    print(f"⚠️ Existing image {base_name} has wrong size ({existing_image.size[0]}x{existing_image.size[1]} vs {atlas_width}x{atlas_height}), creating new")
                existing_image = None
                base_name = self.generate_unique_name(base_name)
            elif settings.atlas_name_handling == 'CREATE_NEW':
                existing_image = None
                base_name = self.generate_unique_name(base_name)
        
        atlas_image = bpy.data.images.new(base_name, width=atlas_width, height=atlas_height)
        return atlas_image, base_name

    def pack_regions_maxrects(self, regions, width, height, padding, allow_rotate=False):
        """Pack regions using a basic MaxRects (best area fit) heuristic."""
        if padding < 0:
            padding = 0

        padded = []
        for r in regions:
            rw = r['width'] + padding * 2
            rh = r['height'] + padding * 2
            padded.append((r, rw, rh))

        free = [(0, 0, width, height)]
        placements = []

        def score_fit(fw, fh, rw, rh):
            return (fw * fh) - (rw * rh)

        def split_free_rect(fx, fy, fw, fh, px, py, pw, ph):
            new_free = []
            if px > fx:
                new_free.append((fx, fy, px - fx, fh))
            if px + pw < fx + fw:
                new_free.append((px + pw, fy, (fx + fw) - (px + pw), fh))
            if py > fy:
                new_free.append((fx, fy, fw, py - fy))
            if py + ph < fy + fh:
                new_free.append((fx, py + ph, fw, (fy + fh) - (py + ph)))
            return new_free

        def prune_free(free_rects):
            pruned = []
            for i, a in enumerate(free_rects):
                ax, ay, aw, ah = a
                contained = False
                for j, b in enumerate(free_rects):
                    if i == j:
                        continue
                    bx, by, bw, bh = b
                    if ax >= bx and ay >= by and ax + aw <= bx + bw and ay + ah <= by + bh:
                        contained = True
                        break
                if not contained and aw > 0 and ah > 0:
                    pruned.append(a)
            return pruned

        # Place larger regions first
        padded.sort(key=lambda x: x[1] * x[2], reverse=True)

        for region, rw, rh in padded:
            best = None
            best_score = None

            region_allow_rotate = allow_rotate and region.get('allow_rotate', True)
            for fx, fy, fw, fh in free:
                # No rotation
                if rw <= fw and rh <= fh:
                    score = score_fit(fw, fh, rw, rh)
                    if best_score is None or score < best_score:
                        best_score = score
                        best = (fx, fy, rw, rh, False)
                # Rotation
                if region_allow_rotate and rh <= fw and rw <= fh:
                    score = score_fit(fw, fh, rh, rw)
                    if best_score is None or score < best_score:
                        best_score = score
                        best = (fx, fy, rh, rw, True)

            if best is None:
                return None

            fx, fy, pw, ph, rotated = best
            px = fx + padding
            py = fy + padding
            
            if rotated:
                place_w, place_h = region['height'], region['width']
            else:
                place_w, place_h = region['width'], region['height']

            placements.append((region, (px, py, place_w, place_h, rotated)))

            new_free = []
            for rx, ry, rw0, rh0 in free:
                if not (fx < rx + rw0 and fx + pw > rx and fy < ry + rh0 and fy + ph > ry):
                    new_free.append((rx, ry, rw0, rh0))
                    continue
                new_free.extend(split_free_rect(rx, ry, rw0, rh0, fx, fy, pw, ph))

            free = prune_free(new_free)

        return placements

    def is_region_rotation_safe(self, face_group, uv_layer, tol=1e-6):
        """Only allow rotation if all UV edges are axis-aligned."""
        for item in face_group:
            face = item['face']
            loops = list(face.loops)
            if len(loops) < 3:
                continue
            for i in range(len(loops)):
                uv1 = loops[i][uv_layer].uv
                uv2 = loops[(i + 1) % len(loops)][uv_layer].uv
                du = abs(uv2.x - uv1.x)
                dv = abs(uv2.y - uv1.y)
                if du > tol and dv > tol:
                    return False
        return True
    
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
    
    def test_packing_rectangular(self, regions, width, height, padding, allow_rotate=False):
        """Test if regions can fit in a rectangular atlas using MaxRects."""
        packed = self.pack_regions_maxrects(regions, width, height, padding, allow_rotate=allow_rotate)
        return packed is not None
    
    def test_packing(self, regions, atlas_size, padding, allow_rotate=False):
        """Test if regions can fit in the given atlas size using MaxRects."""
        packed = self.pack_regions_maxrects(regions, atlas_size, atlas_size, padding, allow_rotate=allow_rotate)
        return packed is not None
    
    def build_atlas(self, total_regions, atlas_size, settings, obj):
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
        atlas_image, final_atlas_name = self.get_or_create_atlas_image(settings, atlas_width, atlas_height, obj)
        atlas_pixels = np.zeros((atlas_height, atlas_width, 4), dtype=np.float32)
        atlas_regions = {}

        packed = self.pack_regions_maxrects(
            total_regions,
            atlas_width,
            atlas_height,
            settings.padding,
            allow_rotate=settings.allow_region_rotation
        )
        if packed is None:
            raise Exception("Packing failed for computed atlas size")

        for region, placement in packed:
            px, py, pw, ph, rotated = placement

            region_pixels = region['pixels']
            if rotated:
                region_pixels = np.rot90(region_pixels)

            for row in range(ph):
                for col in range(pw):
                    atlas_x = px + col
                    atlas_y = py + row
                    if atlas_x < atlas_width and atlas_y < atlas_height:
                        atlas_pixels[atlas_y, atlas_x] = region_pixels[row, col]

            # Store region info for UV remapping
            region_key = f"{region['img_name']}_{region['type']}"
            atlas_regions[region_key] = {
                'atlas_x': px, 'atlas_y': py,
                'width': pw, 'height': ph,
                'u_min': region['u_min'], 'u_max': region['u_max'],
                'v_min': region['v_min'], 'v_max': region['v_max'],
                'faces': region['faces'],
                'type': region['type'],
                'rotated': rotated
            }
        
        # Write pixels to Blender image
        atlas_image.pixels = atlas_pixels.flatten().tolist()
        
        # Save atlas file if requested
        if settings.save_atlas_file:
            base_path = settings.output_dir if settings.output_dir else "//"
            if base_path and not base_path.endswith(("/", "\\")):
                base_path = base_path + "/"
            atlas_image.filepath_raw = f"{base_path}{final_atlas_name}.{settings.atlas_format.lower()}"
            atlas_image.file_format = settings.atlas_format
            atlas_image.save()
        
        if settings.debug_mode:
            print(f"📁 Created atlas image: {final_atlas_name}")
        
        return atlas_image, atlas_regions
    
    def remap_uvs(self, atlas_regions, bm, uv_layer, atlas_width, atlas_height, settings):
        """Remap UVs to atlas coordinates"""
        for region_key, region in atlas_regions.items():
            for item in region['faces']:
                face = item['face']
                for loop in face.loops:
                    old_uv = loop[uv_layer].uv
                    if settings.normalize_uv_ranges:
                        old_u, old_v = self.normalize_uv(old_uv, settings)
                    else:
                        old_u, old_v = old_uv.x, old_uv.y
                    
                    # Calculate normalized coordinates within the original UV region
                    u_norm = (old_u - region['u_min']) / max(0.001, region['u_max'] - region['u_min'])
                    v_norm = (old_v - region['v_min']) / max(0.001, region['v_max'] - region['v_min'])
                    
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
    
    def apply_atlas_material(self, obj, bm, atlas_image, settings):
        """Create new material with atlas texture"""
        mat = bpy.data.materials.new(name=settings.material_name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex_node.image = atlas_image
        mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_node.outputs['Color'])
        
        if settings.preserve_original_materials:
            mat_index = len(obj.data.materials)
            obj.data.materials.append(mat)
        else:
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            mat_index = 0
        
        for face in bm.faces:
            face.material_index = mat_index

    def apply_debug_materials(self, obj, bm, atlas_regions, settings):
        """Create colored materials to visualize region assignments."""
        def color_from_key(key):
            h = abs(hash(key))
            return ((h & 0xFF) / 255.0, ((h >> 8) & 0xFF) / 255.0, ((h >> 16) & 0xFF) / 255.0, 1.0)

        if not settings.preserve_original_materials:
            obj.data.materials.clear()

        region_materials = {}
        for region_key, region in atlas_regions.items():
            if region_key not in region_materials:
                mat = bpy.data.materials.new(name=f"Region_{region_key}")
                mat.use_nodes = True
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    bsdf.inputs['Base Color'].default_value = color_from_key(region_key)
                mat_index = len(obj.data.materials)
                obj.data.materials.append(mat)
                region_materials[region_key] = mat_index

            mat_index = region_materials[region_key]
            for item in region['faces']:
                item['face'].material_index = mat_index


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
            selected_meshes = [o for o in context.selected_objects if o.type == 'MESH']
            if len(selected_meshes) > 1:
                box.label(text=f"Selected: {len(selected_meshes)} mesh objects", icon='OBJECT_DATA')
                box.label(text=f"Active: {obj.name}")
            else:
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
        col.prop(settings, "atlas_name_preset")
        if settings.atlas_name_preset == 'CUSTOM':
            col.prop(settings, "atlas_name_template")
        col.prop(settings, "atlas_name_handling")
        
        # Show info about name handling
        template = settings.atlas_name_template
        if settings.atlas_name_preset == 'ATLAS':
            template = "{atlas}"
        elif settings.atlas_name_preset == 'OBJECT_ATLAS':
            template = "{object}_{atlas}"
        elif settings.atlas_name_preset == 'OBJECT_TIMESTAMP':
            template = "{object}_{timestamp}"
        elif settings.atlas_name_preset == 'ATLAS_TIMESTAMP':
            template = "{atlas}_{timestamp}"
        elif settings.atlas_name_preset == 'CUSTOM':
            template = settings.atlas_name_template

        preview_name = template.format(
            object=obj.name if obj else "Object",
            atlas=settings.atlas_name,
            timestamp="YYYYMMDD_HHMMSS"
        )
        existing_img = bpy.data.images.get(preview_name)
        if existing_img:
            box = layout.box()
            if settings.atlas_name_handling == 'OVERWRITE':
                box.label(text=f"⚠️ Will overwrite existing '{preview_name}'", icon='ERROR')
            elif settings.atlas_name_handling == 'CREATE_NEW':
                box.label(text=f"📝 Will create new name (e.g. '{preview_name}.001')", icon='INFO')
            elif settings.atlas_name_handling == 'USE_EXISTING':
                box.label(text=f"♻️ Will reuse existing '{preview_name}' if compatible", icon='INFO')
        
        col.prop(settings, "save_atlas_file")
        if settings.save_atlas_file:
            col.prop(settings, "atlas_format")
            col.prop(settings, "output_dir")
        
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
            if settings.allow_region_rotation:
                col.prop(settings, "rotation_safe_only")
        
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
            col.prop(settings, "atlas_name_preset")
            if settings.atlas_name_preset == 'CUSTOM':
                col.prop(settings, "atlas_name_template")
            col.prop(settings, "atlas_name_handling")
            col.prop(settings, "save_atlas_file")
            if settings.save_atlas_file:
                col.prop(settings, "atlas_format")
                col.prop(settings, "output_dir")
            
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
