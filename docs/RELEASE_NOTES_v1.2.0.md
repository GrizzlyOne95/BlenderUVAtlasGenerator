# UV Atlas Generator v1.2.0

## Summary

This release promotes the current post-v1.1.1 work into a packaged Blender add-on release, with stronger validation, more flexible output naming, improved texture-source resolution, and faster image processing.

## Added

- Atlas naming presets and custom templates using `{object}`, `{atlas}`, and `{timestamp}`.
- Validation and resolved-name feedback for atlas naming templates.
- Better user-facing validation for output paths and unsaved `.blend` files.

## Changed

- Texture images are resolved from linked shader-graph nodes instead of simply using the first image-texture node found.
- Existing atlas datablocks can be reused correctly when overwrite behavior is selected.
- Region sampling and atlas image writes use NumPy and Blender bulk pixel APIs for substantially less Python-side pixel-loop overhead.
- Output naming and save-path behavior is more predictable for per-object and combined workflows.

## Fixed

- Improved handling of materials whose relevant image texture is not the first texture node in the material.
- Better overwrite behavior for existing atlas images.
- Clearer failure messages when an output file cannot be resolved safely.

## Installation

1. Download `uv_atlas_generator-v1.2.0.zip` from this release.
2. In Blender, open **Edit > Preferences > Add-ons**.
3. Click **Install...** and select the downloaded ZIP.
4. Enable **UV: UV Atlas Generator**.

Requires Blender 3.6 or newer.
