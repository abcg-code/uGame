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

import re

section_aliases = {
    "Normals": "Geometry",
    "Unapplied Transforms": "Geometry",
    "Transforms Applied": "Geometry",
    "Double Vertices": "Geometry",
    "Topology": "Geometry",
    "Counts": "Geometry",

    "Marked Seams": "UVs",
    "Seams": "UVs",
    "Unwrapping Quality": "UVs",
    "Texel Density Ratio": "UVs",

    "Texture name invalid": "Textures",
    "Contains disallowed term": "Textures",
    "Resolution too high for background Asset": "Textures",
    "Resolution too low for Hero Asset": "Textures",
    "Very low resolution": "Textures",
    "Not power-of-two": "Textures",
    "Missing Texture Map": "Textures",

    "Modifier": "Modifiers",
    "Modifiers": "Modifiers",
    
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

def normalize_token(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', s.lower())

required_maps = {
    "Diffuse": {normalize_token(s) for s in {"_c", "_col", "_color", "_bc", "_basecolor", "_base_color", "_albedo", "_d", "_diffuse", "_diff"}},
    "Normal": {normalize_token(s) for s in {"_n", "_nrm", "_normal", "_h", "_height", "_nml"}},
    "Roughness": {normalize_token(s) for s in {"_r", "_roughness", "_rma", "_rough", "_rgh", "_orm", "_mrh"}}
}

optional_maps = {
    "Metallic": {normalize_token(s) for s in {"_m", "_mt", "_mtl", "_metalness", "_metallic", "_rma", "_met", "_orm"}},
    "Emissive": {normalize_token(s) for s in {"_e", "_ems", "_emmissive", "_g", "_glow"}},
    "Specular": {normalize_token(s) for s in {"_s", "_spec", "_specular"}},
    "Ambient Occlusion": {normalize_token(s) for s in {"_ao", "_a", "_occlusion", "_rma", "_orm"}},
    "Alpha": {normalize_token(s) for s in {"_a", "_alpha", "_mask", "_opacity"}}
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
