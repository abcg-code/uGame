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
}

required_maps = {
    "Diffuse": {"_c", "_col", "_color", "_basecolor", "albedo", "diffuse"},
    "Normal": {"_n", "_nrm", "_normal"},
    "Roughness": {"_r", "_roughness", "_rma"},
}

optional_maps = {
    "Metallic": {"_m", "_metallic", "_rma"},
    "Emissive": {"_e", "_emmissive"},
    "Specular": {"_s", "_spec", "_specular"},
    "Ambient Occlusion": {"_ao", "_occlusion", "_rma"}
}

banned_patterns = ["default*", "material*", "texture*",
    "image*", "untitled*", "placeholder*", "bake*",
    "temp*", "test*", "preview*", "render*", "output*",
    "copy*", "duplicate*", "backup*", "old*", "new*"
]

TEXEL_DENSITY_RANGE = (3, 12)
TEXEL_DENSITY_MIN_AAA = 12
TEXEL_DENSITY_DEVIATION_THRESHOLD = 0.15
UV_UTILIZATION_MIN = 90
