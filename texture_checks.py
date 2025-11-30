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

import os
import re
import fnmatch
from .helpers import (
    is_hero_asset
)
from .constants import (
    normalize_token,
    valid_prefixes,
    required_maps,
    optional_maps,
    banned_patterns
)

def infer_map_type(name_clean):
    token = normalize_token(name_clean)
    for map_type, suffixes in required_maps.items():
        for suffix in suffixes:
            if token.endswith(suffix):
                # print("Matched", map_type, "with suffix", suffix, "for token", token)
                return map_type
    for map_type, suffixes in optional_maps.items():
        for suffix in suffixes:
            if token.endswith(suffix):
                # print("Matched", map_type, "with suffix", suffix, "for token", token)
                return map_type
    return None

def get_clean_name(img):
    name_raw = os.path.splitext(img.name)[0]
    return re.sub(r'[-_]?\d{3,5}x\d{3,5}$', '', name_raw).lower()

def get_clean_map_type(img):
    return infer_map_type(get_clean_name(img))

def detect_map_type_from_node(node):
    if node.type == 'TEX_IMAGE':
        for link in node.outputs['Color'].links:
            target = link.to_node
            if target.type == 'NORMAL_MAP':
                return "Normal"
            if target.type == 'SEPARATE_COLOR':
                return "Roughness"
            if target.type in {'BSDF_PRINCIPLED', 'BSDF_DIFFUSE'}:
                for sock in target.inputs:
                    if sock.name.lower() in {"base color", "color"}:
                        return "Diffuse"
    return None

def check_texture_naming(img, strict):
    report = []
    name = img.name
    name_lower = name.lower()
    name_clean = get_clean_name(img)
    token = normalize_token(name_clean)
    map_type = infer_map_type(name_clean)

    all_suffixes = set().union(*required_maps.values(), *optional_maps.values())
    has_valid_suffix = any(token.endswith(suffix) for suffix in all_suffixes)
    if not has_valid_suffix:
        report.append(("Texture name invalid", img.name, "ERROR"))

    if map_type:
        suffixes = required_maps.get(map_type, set()) | optional_maps.get(map_type, set())
        if not any(token.endswith(suffix) for suffix in suffixes):
            report.append(("Missing required suffix", map_type, "ERROR"))

    if strict:
        for mt, suffixes in optional_maps.items():
            if normalize_token(mt) in token:
                if not any(token.endswith(suffix) for suffix in suffixes):
                    report.append(("Missing optional suffix", mt, "WARNING"))

    if any(fnmatch.fnmatch(name_lower, pattern) for pattern in banned_patterns):
        report.append(("Contains disallowed term", name, "ERROR"))

    if strict and not any(name.startswith(prefix) for prefix in valid_prefixes):
        report.append(("Missing valid prefix (T_ or TEX_)", name, "WARNING"))
    # print("token:", token)
    # print("suffixes for Roughness:", required_maps["Roughness"])
    return report

def check_texture_resolution(img):
    report = []
    w, h = img.size
    min_dim = min(w, h)

    if min_dim < 256:
        report.append((f"Very low resolution ({w}x{h})", f"{img.name}", "ERROR"))
    elif is_hero_asset() and min_dim < 2048:
        report.append((f"Resolution too low for Hero Asset ({w}x{h})", f"{img.name}", "ERROR"))
    elif not is_hero_asset() and min_dim > 1024:
        report.append((f"Resolution too high for background Asset ({w}x{h})", f"{img.name}", "ERROR"))
    elif min_dim < 512:
        report.append((f"Low resolution ({w}x{h})", f"{img.name}", "WARNING"))
    else:
        report.append((f"Resolution OK ({w}x{h})", f"{img.name}", "INFO"))

    pot = (w & (w -1) == 0) and (h & (h - 1) == 0)
    if not pot:
        report.append((f"Not power-of-two ({w}x{h})", f"{img.name}", "ERROR"))
    
    return report

def is_node_connected(node):
    visited = set()
    to_visit = list(node.outputs)

    while to_visit:
        socket = to_visit.pop()
        for link in socket.links:
            target_node = link.to_node
            if target_node not in visited:
                visited.add(target_node)
                to_visit.extend(target_node.outputs)
    return bool(visited)