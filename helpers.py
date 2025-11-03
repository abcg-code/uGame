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

import bpy
import bmesh
from mathutils import Vector, geometry

def is_location_applied(obj):
    has_parent = obj.parent is not None
    is_zero = all(val == 0.0 for val in obj.location)
    return has_parent or is_zero

def get_top_parent(obj):
    while obj.parent:
        obj = obj.parent
    return obj

def get_transform_status(obj):
    scale_applied = all(round(val, 3) == 1.0 for val in obj.scale)
    rotation_applied = all(round(val, 3) == 0.0 for val in obj.rotation_euler)
    location_applied = all(round(val, 3) == 0.0 for val in obj.location)
    return scale_applied, rotation_applied, location_applied

def calculate_uv_area(face, uv_layer):
    uv_coords = [loop[uv_layer].uv for loop in face.loops]
    if len(uv_coords) < 3:
        return 0.0

    area = 0.0
    for i in range(1, len(uv_coords) -1):
        a = uv_coords[0]
        b = uv_coords[i]
        c = uv_coords[i + 1]
        area += geometry.area_tri(a, b, c)

    return area

def get_island_texel_densities(obj):
    if obj.type != 'MESH':
        return 0.0, 0.0

    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active

    if not uv_layer:
        bm.free()
        return 0.0, 0.0

    densities = []

    for face in bm.faces:
        face.select = True
        face_area = face.calc_area()

        uv_area = calculate_uv_area(face, uv_layer)

        if face_area > 0:
            density = uv_area / face_area
            densities.append(density)

        face.select = False

    bm.free()

    if not densities:
        return 0.0, 0.0

    avg_density = sum(densities) / len(densities)
    deviation = max(abs(d - avg_density) for d in densities)
    return avg_density, deviation

def get_uv_utilization(obj):
    if obj.type != 'MESH':
        return 0.0, False

    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    if not uv_layer:
        return 0.0, False
    
    uvs = [loop.uv for loop in uv_layer.data]
    if not uvs:
        return 0.0, False
    
    min_uv, max_uv = get_uv_bounds(uvs)
    uv_area = (max_uv.x - min_uv.x) * (max_uv.y - min_uv.y)

    clamped_min = Vector((
        max(0.0, min(min_uv.x, 1.0)),
        max(0.0, min(min_uv.y, 1.0))
    ))
    clamped_max = Vector((
        max(0.0, min(min_uv.x, 1.0)),
        max(0.0, min(min_uv.y, 1.0))
    ))
    
    clamped_area = (clamped_max.x - clamped_min.x) * (clamped_max.y - clamped_min.y)

    overflow = uv_area > 1.0 or max_uv.x > 1.0 or max_uv.y >1.0 or min_uv.x < 0.0 or min_uv.y < 0.0
    utilization_percent = round(clamped_area * 100, 2)

    return utilization_percent, overflow

def get_uv_bounds(uvs):
    min_uv = Vector((min(uv.x for uv in uvs), min(uv.y for uv in uvs)))
    max_uv = Vector((max(uv.x for uv in uvs), max(uv.y for uv in uvs)))
    return min_uv, max_uv

def get_all_objects_recursive(collection):
    objs = list(collection.objects)
    for child in collection.children:
        objs.extend(get_all_objects_recursive(child))
    return objs

