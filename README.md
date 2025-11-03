uGame Add-on for Blender

Validate game-readiness of Blender assest with fast, visual feedback.


## Features
- Checks geometry, textures, UVs, modifiers, and rigging
- Clear summaries with warnings
- Topbar intergration with custom icon
- Configurable scan modes and asset flags


## Instalation
1. Download the '.zip' from [Releases](https://github.com/abcg-code/uGame/releases)
2. Drag and drop the '.zip' into Blender

## Alternatively
1. Download the '.zip' from [Releases](https://github.com/abcg-code/uGame/releases)
2. In Blender: 'Edit > Preferences > Add-ons > Install'
3. Select the '.zip' and enable **uGame**


## Quick Start
1. Click the gamepad icon in the topbar
2. Adjust scan settings
    - Exclude highpoly meshes (Enabled by default)
    - Asset Collection Mode
    - AAA Game Check
    - Hero Asset check
    - Scan Mode (File, Selected, or Collection)
3. Run the checks and review the report


## What it checks

**Geometry**
- Unapplied transforms (Location, Rotation, Scale)
- Non-manifold edges
- Flipped Normals
- Stray/Double vertices
- N-gons

**Textures**
- Missing maps (Diffuse, Normal, Roughness as standard)
- Resolution mismatches
- Filename issues (e.g. standard suffix naming)

**UVs**
- Missing UV maps
- Unwrapping quality
- Texel density
- UV space optimization

**Modifiers**
- Non-applied modifiers

**Rigging**
- Bone count
- Constraints
- Vertex group coverage


## Summary Output
- Per-object detail blocks
- Final summary with game-readiness status
- Section breakdowns (Geometry, Texture, etc.)
- Warnings and errors clearly labeled


## Tips
- Info and Warnings are shown even if the asset passes
- Use Asset Collection Mode to relax location checks (e.g. Modular game assets or collections)


## License
GNU General Public License (GPL)

