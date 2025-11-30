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
from .helpers import (
    get_uv_bounds
)
from .checks import (
    check_geometry,
    check_uvs,
    check_textures,
    check_rigging,
    check_object_modifiers
)

def set_scan_mode(settings, mode):
    settings.scan_single_object = (mode == "single")
    settings.scan_selected_collection = (mode == "collection")
    settings.scan_entire_file = (mode == "file")

def is_high_poly(obj):
            name_check = obj.name.lower().endswith("_high")
            collection_check = any(col.name.lower() == "high poly" for col in obj.users_collection)
            return name_check or collection_check

def get_active_collection():
    alc = bpy.context.view_layer.active_layer_collection
    if alc:
        return alc.collection
    obj = bpy.context.active_object
    if obj and obj.users_collection:
        return obj.users_collection[0]
    return None

def get_selected_collection():
    for item in bpy.context.selected_ids:
        if isinstance(item, bpy.types.Collection):
            return item
    return None

def get_selected_collection_objects():
    col = get_active_collection()
    if not col:
        return []
    return [o for o in col.objects if o.type in {'MESH', 'ARMATURE'}]

def get_all_nested_collection_objects(root_collection=None, types={'MESH', 'ARMATURE'}):
    if root_collection is None:
        root_collection = get_active_collection()
        if root_collection is None:
            return []

    def gather_objects(col):
        objs = [obj for obj in col.objects if obj.type in types]
        for child in col.children:
            objs.extend(gather_objects(child))
        return objs

    return gather_objects(root_collection)

def get_all_objects_in_collection(collection, types={'MESH', 'ARMATURE'}):
    objects = [obj for obj in collection.objects if obj.type in types]
    for child in collection.children:
        objects.extend(get_all_objects_in_collection(child))
    return objects

def get_collection_uv_utilization(collection):
    report = []
    all_uvs = []

    for obj in collection.objects:
        if obj.type != 'MESH':
            continue
        mesh = obj.data
        uv_layer = mesh.uv_layers.active
        if not uv_layer:
            continue
        all_uvs.extend([loop.uv.copy() for loop in uv_layer.data])

    if not all_uvs:
        report.append(("UV Space Utilization", "No UVs found", "WARNING"))
        return report

    min_uv , max_uv = get_uv_bounds(all_uvs)
    uv_area = (max_uv.x - min_uv.x) * (max_uv.y - min_uv.y)
    utilization = round(uv_area * 100, 2)

    level = "INFO" if utilization >= 90 else "WARNING"
    report.append(("UV Space Utilization", f"{utilization}%", level))
    return report

