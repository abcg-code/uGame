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
from .constants import (
    valid_prefixes,
    required_maps,
    optional_maps,
    banned_patterns
)

def infer_map_type(name_clean):
    for map_type, suffixes in required_maps.items():
        if any(name_clean.endswith(suffix) for suffix in suffixes):
            return map_type
    for map_type, suffixes in optional_maps.items():
        if any(name_clean.endswith(suffix) for suffix in suffixes):
            return map_type
    return None

def get_clean_name(img):
    name_raw = os.path.splitext(img.name)[0]
    return re.sub(r'[-_]?\d{3,5}x\d{3,5}$', '', name_raw).lower()

def get_clean_map_type(img):
    return infer_map_type(get_clean_name(img))

def check_texture_filename(img, strict):
    report = []
    name = img.name
    name_lower = name.lower()
    name_no_ext = os.path.splitext(name)[0]
    resolution_pattern = r'[-_]?\d{3,5}x\d{3,5}$'
    has_resolution_tag = re.search(resolution_pattern, name_no_ext)

    if strict and has_resolution_tag:
        report.append(("Filename includes resolution", name, "ERROR"))
    elif has_resolution_tag:
        report.append(("Filename includes resolution", name, "WARNING"))

    if any(fnmatch.fnmatch(name_lower, pattern) for pattern in banned_patterns):
        report.append(("Contains disallowed term", name, "ERROR"))

    if strict and not any(name.startswith(prefix) for prefix in valid_prefixes):
        report.append(("Missing valid prefix (T_ or TEX_)", name, "WARNING"))

    return report

def check_texture_suffix(img, strict):
    report = []
    name_clean = get_clean_name(img)
    map_type = infer_map_type(name_clean)

    all_suffixes = set().union(*required_maps.values(), *optional_maps.values())

    has_valid_suffix = any(name_clean.endswith(suffix) for suffix in all_suffixes)

    if not has_valid_suffix:
        report.append(("Texture name invalid", img.name, "ERROR"))

    if map_type:
        suffixes = required_maps.get(map_type, set()) | optional_maps.get(map_type, set())
        if not any(name_clean.endswith(suffix) for suffix in suffixes):
            report.append((f"Missing required suffix for {map_type}", img.name, "ERROR"))

    if strict:
        for map_type, suffixes in optional_maps.items():
            if map_type.lower() in name_clean:
                if not any(name_clean.endswith(suffix) for suffix in suffixes):
                    report.append((f"Missing optional suffix for {map_type}", img.name, "WARNING"))

    return report

def check_texture_resolution(img, is_hero_asset):
    report = []
    w, h = img.size
    min_dim = min(w, h)

    if min_dim < 256:
        report.append((f"Very low resolution ({w}x{h})", img.name, "ERROR"))
    elif is_hero_asset and min_dim < 2048:
        report.append((f"Resolution too low for Hero Asset ({w}x{h})", img.name, "ERROR"))
    elif not is_hero_asset and min_dim > 1024:
        report.append((f"Resolution too high for background Asset ({w}x{h})", img.name, "ERROR"))
    elif min_dim < 512:
        report.append((f"Low resolution ({w}x{h})", img.name, "INFO"))
    else:
        report.append((f"Resolution OK ({w}x{h})", img.name, "INFO"))

    pot = (w & (w -1) == 0) and (h & (h - 1) == 0)
    if not pot:
        report.append((f"Not power-of-two ({w}x{h})", img.name, "ERROR"))
    
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