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

def is_color_atlas(obj, utilization, uvs, has_normal, has_roughness):
    if not uvs:
        return False

    unique_uvs = set(uv.to_tuple() for uv in uvs)
    unique_ratio = len(unique_uvs) / len(uvs)

    return (
        utilization < 10.0 and
        unique_ratio < 0.1 and
        not has_normal and
        not has_roughness
    )

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
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active

    if not uv_layer:
        bm.free()
        return 0.0, False, []

    uvs = []
    min_u, min_v = 1.0, 1.0
    max_u, max_v = 0.0, 0.0
    overflow = False

    try:
        for face in bm.faces:
            for loop in face.loops:
                uv = loop[uv_layer].uv
                uvs.append(uv)
                u, v = uv.x, uv.y

                min_u = min(min_u, u)
                min_v = min(min_v, v)
                max_u = max(max_u, u)
                max_v = max(max_v, v)

                if u < 0.0 or u > 1.0 or v < 0.0 or v > 1.0:
                    overflow = True
    except Exception as e:
        print(f"UV read error: {e}")
        bm.free()
        return 0.0, False, []

    bm.free()

    width = max_u - min_u
    height = max_v - min_v
    utilization = round(width * height * 100, 2) if uvs else 0.0

    return utilization, overflow, uvs

def get_uv_bounds(uvs):
    min_uv = Vector((min(uv.x for uv in uvs), min(uv.y for uv in uvs)))
    max_uv = Vector((max(uv.x for uv in uvs), max(uv.y for uv in uvs)))
    return min_uv, max_uv

def get_all_objects_recursive(collection):
    objs = list(collection.objects)
    for child in collection.children:
        objs.extend(get_all_objects_recursive(child))
    return objs

def count_uv_islands(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        return 0

    visited_faces = set()
    islands = 0

    for face in bm.faces:
        if face in visited_faces:
            continue

        stack = [face]
        connected = set()

        while stack:
            current = stack.pop()
            if current in visited_faces:
                continue
            visited_faces.add(current)
            connected.add(current)

            for edge in current.edges:
                if not edge.seam:
                    for linked_face in edge.link_faces:
                        if linked_face not in visited_faces:
                            stack.append(linked_face)

        if connected:
            islands += 1
    
    bm.free()
    return islands

def get_total_uv_and_face_area(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.active

    total_uv_area = 0.0
    total_face_area =0.0
    if uv_layer:
        for face in bm.faces:
            face_area = face.calc_area()
            total_face_area += face_area
            uv_area = calculate_uv_area(face, uv_layer)
            total_face_area += uv_area

    bm.free()
    return total_uv_area, total_face_area

def is_uv_layout_stacked(uvs, threshold=0.1):
    if not uvs:
        return False
    unique_uvs = set(uv.to_tuple() for uv in uvs)
    return len(unique_uvs) / len(uvs) < threshold