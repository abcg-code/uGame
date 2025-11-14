'''
Copyright (C) 2025 - Autotroph
https://autotroph.com

Created by Adrian Bellworthy

This file is part of uGame.

uGame is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see https://www.gnu.org/licenses.
'''

section_aliases = {
    "Unapplied Transforms": "Transforms",
    "Transforms Applied": "Transforms",
    "Missing Texture Map: Diffuse": "Textures",
    "Missing Texture Map: Normal": "Textures",
    "Missing Texture Map: Roughness": "Textures",
    "Missing Texture Map: Metallic": "Textures",
    "Missing Texture Map: Emissive": "Textures",
    "Missing Texture Map: Specular": "Textures",
    "Missing Texture Map: Ambient Occlusion": "Textures",
    "Marked Seams": "UVs",
    "Unwrapping Quality": "UVs",
    "Texel Density Ratio": "UVs",
    "Modifier": "Modifiers",
    "Modifiers": "Modifiers",
    "Normals": "Geometry",
    "Bone Count": "Rigging",
    "Bone Naming OK": "Rigging",
    "Hierarchy": "Rigging",
    "Naming Convention": "Rigging",
    "Blacklisted Bone Names": "Rigging",
    "Constraints Present": "Rigging",
    "Drivers Present": "Rigging",
    "Unassigned Verts": "Rigging",
    "Rigging Context": "Rigging"
}

valid_prefixes = ["T_", "TEX_"]

required_maps = {
    "Diffuse": {s.lower() for s in {"_c", "_col", "_color", "_basecolor", "_base_color", "_albedo", "_diffuse"}},
    "Normal": {s.lower() for s in {"_n", "_nrm", "_normal", "_h", "_height"}},
    "Roughness": {s.lower() for s in {"_r", "_roughness", "_rma"}}
}

optional_maps = {
    "Metallic": {s.lower() for s in {"_m", "_metallic", "_rma"}},
    "Emissive": {s.lower() for s in {"_e", "_emmissive"}},
    "Specular": {s.lower() for s in {"_s", "_spec", "_specular"}},
    "Ambient Occlusion": {s.lower() for s in {"_ao", "_occlusion", "_rma"}},
    "Alpha": {s.lower() for s in {"_a", "_alpha", "_o", "_opacity"}}
}

banned_patterns = ["default*", "material*", "texture*",
    "image*", "untitled*", "placeholder*", "bake*",
    "temp*", "test*", "preview*", "render*", "output*",
    "copy*", "duplicate*", "backup*", "old*", "new*"
]

allowed_prefixes = (
    "DEF-", "CTRL-", "MCH-", "VIS-", "TGT-"
)

blacklist_patterns = {
    "Bone*", "Joint*", "Temp*", "Unnamed*", "Helper*"
}

TEXEL_DENSITY_RANGE = (3, 12)
TEXEL_DENSITY_MIN_AAA = 12
TEXEL_DENSITY_DEVIATION_THRESHOLD = 0.15
UV_UTILIZATION_MIN = 90
