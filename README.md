# BlenderUVAtlasGenerator
Ports shader materials to a raw atlas, while preserving all original UV layouts and islands

<img width="1570" height="718" alt="before" src="https://github.com/user-attachments/assets/2dd7a89f-1240-45a4-9307-b2bb11ac3415" />

<img width="1549" height="629" alt="after" src="https://github.com/user-attachments/assets/21b5cb67-7c02-4bd2-925a-5f49801f8c77" />

# UV Atlas Generator for Blender

A powerful Blender addon that generates optimized UV atlases with automatic mirror detection and smart texture packing.

![Addon Interface](images/interface.png)

## ✨ Features

- **Automatic Mirror Detection** - Detects mirrored UV faces and handles them properly
- **Smart Texture Packing** - MaxRects bin-packing with optional rotation
- **Batch Processing** - Generate atlases for multiple selected mesh objects
- **Flexible Naming & Output** - Output directory and naming presets/templates
- **Flexible Atlas Sizing** - Power-of-2, non-power-of-2, and rectangular atlas support
- **Quality Presets** - Game Ready, High Quality, Mobile, and Custom presets
- **Advanced UV Processing** - Proper texture sampling with wrapping modes
- **Material Integration** - Automatically creates atlas materials
- **Debug Mode** - Detailed console output for troubleshooting

## 🚀 Installation

### Quick Install (Recommended)

1. **Download the addon:**
   - Click the green "Code" button above → "Download ZIP"
   - Extract the ZIP file
   - Locate the `uv_atlas_generator` folder

2. **Install in Blender:**
   - Open Blender
   - Go to `Edit` → `Preferences` → `Add-ons`
   - Click `Install...`
   - Select the ZIP you downloaded (or the `uv_atlas_generator` folder)
   - Enable "UV: UV Atlas Generator"

3. **Find the addon:**
   - Open the 3D Viewport
   - Press `N` to open the sidebar
   - Look for the "UV Atlas" tab

### Alternative: Release Download

1. Go to [Releases](../../releases)
2. Download the addon ZIP from the latest release
3. Follow installation steps above

## 📋 Requirements

- **Blender:** 3.6.0 or newer
- **Python Libraries:** numpy (usually included with Blender)
- **Object Requirements:** Mesh object with materials and textures

## 🎯 Quick Start

1. **Select a mesh object** with materials and textures
2. **Switch to Object mode**
3. **Open the UV Atlas panel** (3D Viewport sidebar → UV Atlas tab)
4. **Choose a preset:**
   - **Game Ready** - Balanced quality/performance (2048px)
   - **High Quality** - Maximum detail (4096px)
   - **Mobile** - Optimized for mobile (1024px)
   - **Custom** - Manual configuration
5. **Click "Generate UV Atlas"**

## 🛠️ Usage Guide

### Basic Workflow

```
Select Mesh → Configure Settings → Generate Atlas → New Material Applied
```

### Mirror Detection Modes

- **Auto Detect** - Automatically detects mirrored faces by UV winding
- **Force Regular** - Treats all faces as regular (no mirroring)
- **Force Mirrored** - Treats all faces as mirrored
- **Manual Selection** - Use custom flip settings

### Packing Algorithms

- **Insertion Order** - MaxRects packing using original order
- **Size Sorted** - MaxRects packing, sorted by area (recommended)
- **Best Fit** - MaxRects packing, sorted by long edge

### Atlas Sizing

- **Force Square** - Creates square atlases (power of 2)
- **Allow Non-Power-of-2** - Enables custom sizes
- **Rectangular** - Allows non-square dimensions for better efficiency

## ⚙️ Advanced Settings

Click "Show Advanced Options" to access:

- **UV Processing** - Coordinate normalization and precision
- **Output Control** - File naming and format options
- **Material Settings** - Atlas material creation options
- **Debug Mode** - Console output for troubleshooting

## 📊 Performance Tips

- **Use Size Sorted packing** for best balance of speed/quality
- **Enable region rotation** for maximum efficiency
- **Adjust target region size** based on your texture detail needs
- **Use appropriate atlas sizes** - bigger isn't always better

## 🐛 Troubleshooting

### Common Issues

**"No mesh object selected"**
- Select a mesh object and switch to Object mode

**"Object has no materials"**
- Ensure your object has materials with image textures

**"No valid materials with textures found"**
- Check that materials use Shader Editor with Image Texture nodes

**Atlas appears empty**
- Enable Debug Mode to see detailed console output
- Check UV coordinates are within reasonable ranges

### Debug Mode

Enable "Debug Mode" in advanced settings to see detailed information:
- Processing statistics
- Atlas efficiency metrics
- Region packing details
- Error diagnostics

## 🤝 Contributing

Contributions are welcome! Please feel free to:

- Report bugs via [Issues](../../issues)
- Suggest features via [Discussions](../../discussions)
- Submit pull requests for improvements

### Development Setup

```bash
git clone https://github.com/yourusername/blender-uv-atlas-generator.git
cd blender-uv-atlas-generator
# Install the addon in Blender for testing
```

## 📝 Changelog

### v1.0.0 (Initial Release)
- UV atlas generation with mirror support
- Multiple packing algorithms
- Quality presets
- Advanced configuration options
- Debug mode and console output

### v1.1.0
- MaxRects bin-packing with rotation safety
- Multi-object batch atlas generation
- Output directory selection and naming presets/templates

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for the Blender community
- Inspired by industry UV atlas workflows
- Thanks to all beta testers and contributors

---

**Made with ❤️ for Blender artists everywhere**

*If this addon helps your workflow, consider giving it a ⭐ star!*
