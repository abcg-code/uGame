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
import fnmatch
import mathutils
from .helpers import (
    is_location_applied,
    get_top_parent,
    get_transform_status,
    get_island_texel_densities,
    get_uv_utilization,
    get_uv_bounds,
    get_all_objects_recursive,
    calculate_uv_area
)
from .constants import (
    required_maps,
    optional_maps,
    TEXEL_DENSITY_RANGE,
    TEXEL_DENSITY_MIN_AAA,
    TEXEL_DENSITY_DEVIATION_THRESHOLD,
    UV_UTILIZATION_MIN
)
from .texture_checks import (
    check_texture_filename,
    check_texture_suffix,
    check_texture_resolution,
    is_node_connected,
    infer_map_type
)

def check_collection_structure(collection):
    report = []

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    
    obj_types = {obj.type for obj in collection.objects}
    if "ARMATURE" not in obj_types:
        report.append((collection.name, "No armature present", "WARNING"))

    if collection.children:
        child_names = ", ".join(child.name for child in collection.children)
        report.append((collection.name, f"Contains nested collections: {child_names}", "INFO"))

    return report

def check_collection_transforms(collection):
    report = []

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    objects = [obj for obj in get_all_objects_recursive(collection) if obj.type in {'MESH', 'ARMATURE'}]
    if not objects:
        report.append((collection.name, "No mesh or armature objects to check", "INFO"))
        return report

    report.append((collection.name, f"Checked {len(objects)} objects across nested collections", "INFO"))

    scale_ok = []
    rotation_ok = []
    location_ok = []

    for obj in objects:
        top = get_top_parent(obj)
        scale_ok.append(all(val == 1.0 for val in top.scale))
        rotation_ok.append(all(val == 0.0 for val in top.rotation_euler))
        location_ok.append(is_location_applied(top))
        
    if all(scale_ok):
        report.append((collection.name, "All objects have scale applied", "INFO"))
    else:
        report.append((collection.name, "Some objects have unapplied scale", "WARNING"))

    if all(rotation_ok):
        report.append((collection.name, "All objects have rotation applied", "INFO"))
    else:
        report.append((collection.name, "Some objects have unapplied rotation", "WARNING"))

    if all(location_ok):
        report.append((collection.name, "All objects have valid location", "INFO"))
    else:
        report.append((collection.name, "At least one object has invalid location", "WARNING"))

    return report

def check_flipped_normals(obj):
    if obj.type != 'MESH':
        return 0


    mesh = obj.data
    flipped_count = 0

    for poly in mesh.polygons:
        center = poly.center
        normal = poly.normal
        if normal.dot(center.normalized()) < 0:
            flipped_count += 1

    return flipped_count

def check_counts(obj):
    mesh = obj.data
    return [
        ("Vertex Count", str(len(mesh.vertices)), "INFO"),
        ("Face Count", str(len(mesh.polygons)), "INFO"),
        ("Edge Count", str(len(mesh.edges)), "INFO"),
    ]

def check_bmesh_topology(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    stray_verts = sum(1 for v in bm.verts if not v.link_edges)

    bm.free()
    return [
        ("N-gons", str(ngons), "ERROR" if ngons > 0 else "INFO"),
        ("Non-Manifold Edges", str(non_manifold), "WARNING" if non_manifold > 0 else "INFO"),
        ("Stray Vertices", str(stray_verts), "ERROR" if stray_verts > 0 else "INFO"),
    ]

def check_transforms(obj, settings):
    scale_applied = all(round(val, 3) == 1.0 for val in obj.scale)
    rotation_applied = all(round(val, 3) == 0.0 for val in obj.rotation_euler)
    location_applied = is_location_applied(obj)

    if scale_applied and location_applied and rotation_applied:
        return [("Transforms Applied", "True", "INFO")]

    reasons = []
    if not scale_applied:
        reasons.append("Scale")
    if not rotation_applied:
        reasons.append("Rotation")
    if not location_applied:
        reasons.append("Location")

    level = "ERROR"
    if settings.asset_collection_mode and "Location" in reasons:
        reasons.remove("Location")
        if reasons:
            level = "ERROR"
        else:
            level = "WARNING"
            reasons.append("Location")

    return [("Unapplied Transforms", ", ".join(reasons), level)]

def check_normals(obj):
    flipped = check_flipped_normals(obj)
    if flipped > 0:
        return [("Normals", f"{flipped} faces appear flipped", "WARNING")]
    return [("Normals", "No flipped normals detected", "INFO")]

def check_double_vertices(obj, threshold=0.0001):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    kd = mathutils.kdtree.KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    double_count = 0
    for v in bm.verts:
        matches = kd.find_range(v.co, threshold)
        if len(matches) > 1:
            double_count += 1

    bm.free()
    if double_count > 0:
        return [("Double Vertices: ", f"{double_count} within {threshold}m", "ERROR")]
    return [("Double Vertices: ", "None found", "INFO")]

def check_geometry(obj, settings):
    report = []

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    if obj.type != 'MESH':
        return report

    report.extend(check_counts(obj))
    report.extend(check_bmesh_topology(obj))
    report.extend(check_transforms(obj, settings))
    report.extend(check_normals(obj))
    report.extend(check_double_vertices(obj))

    return report

def check_object_modifiers(obj):
    report = []

    allowed = {"ARMATURE", "TRIANGULATE", "WEIGHTED_NORMAL"}
    disallowed = [mod for mod in obj.modifiers if mod.type not in allowed]
    if disallowed:
        for mod in disallowed:
            report.append((f"Modifier: {mod.name}", f"Disallowed type: {mod.type}", "ERROR"))
    else:
        if obj.modifiers:
            report.append(("Modifiers", "Only allowed modifiers present", "INFO"))
        else:
            report.append(("Modifiers", "None present", "INFO"))

    return report

def check_uvs(obj):
    report = []

    if obj.type != 'MESH':
        return []

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    mesh = obj.data
    uv_unwrapped = bool(mesh.uv_layers)
    seams_exist = any(edge.use_seam for edge in mesh.edges)

    report.append(("UV Unwrapped", str(uv_unwrapped), "INFO" if uv_unwrapped else "ERROR"))
    report.append(("Marked Seams", "Found" if seams_exist else "None",  "INFO" if seams_exist else "ERROR"))

    if uv_unwrapped and not seams_exist:
        report.append(("Unwrapping Quality", "Likely default UVs", "ERROR"))

    if uv_unwrapped:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        uv_layer = bm.loops.layers.uv.active

        if uv_layer:
            total_uv_area = 0.0
            total_face_area = 0.0

            for face in bm.faces:
                face_area = face.calc_area()
                total_face_area =+ face_area
                uv_area = calculate_uv_area(face, uv_layer)
                total_uv_area += uv_area

        bm.free()

        aaa_mode = bpy.context.scene.ugame_settings.aaa_game_check
        ratio = round(total_uv_area / total_face_area, 2) if total_face_area > 0 else 0
        passed = ratio >= TEXEL_DENSITY_MIN_AAA if aaa_mode else TEXEL_DENSITY_RANGE[0] <= ratio <= TEXEL_DENSITY_RANGE[1]
        report.append(("Texel Density Ratio (px/cm)", str(ratio), "INFO" if passed else "WARNING"))

    avg_density, deviation = get_island_texel_densities(obj)
    report.append(("Texel Density Avg", f"{round(avg_density, 2)}", "INFO"))
    report.append(("Texel Density Deviation", f"{round(deviation, 2)}", "WARNING" if deviation > TEXEL_DENSITY_DEVIATION_THRESHOLD * avg_density else "INFO"))

    utilization, overflow = get_uv_utilization(obj)
    aaa_mode = bpy.context.scene.ugame_settings.aaa_game_check
    target = 90.0 if aaa_mode else 80.00
    pass_threshold = 85.0 if aaa_mode else 70.0

    if utilization == 0.0:
        report.append(("UV Space Utilization", "UV layer exists but contains no data", "WARNING"))
    elif overflow:
        report.append(("UV Space Utilization", f"{utilization}% (UVs exceed 0-1 space)", "WARNING"))
    elif utilization >= pass_threshold:
        report.append(("UV Space Utilization", f"{utilization}%", "INFO"))
    elif utilization >= target - 5:
        report.append(("UV Space Utilization", f"{utilization}% (suboptimal)", "WARNING"))
    else:
        report.append(("UV Space Utilization", f"{utilization}% (too low)", "ERROR"))

    if aaa_mode:
        report.append(("AAA Target", "UV Utilization should be ~90%", "INFO"))

    return report

def check_textures(obj):
    report = []
    used_images = set()
    found_maps = set()

    strict = bpy.context.scene.ugame_settings.aaa_game_check
    is_hero_asset = bpy.context.scene.ugame_settings.is_hero_asset

    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if not mat or not mat.use_nodes:
            continue

        for node in mat.node_tree.nodes:
            if node.type != 'TEX_IMAGE' or not node.image:
                continue

            img = node.image
            used_images.add(img)

            for check_fn in [check_texture_filename, check_texture_suffix,check_texture_resolution]:
                arg = strict if check_fn != check_texture_resolution else is_hero_asset
                for label, value, level in check_fn(img, arg):
                    report.append((f"[{img.name}] {label}", "", level))
            
            if img.source == 'TILED':
                tile_count = len(img.tiles)
                report.append((f"[{mat.name}] UDIM detected", f"{tile_count} tiles", "INFO"))

            map_type = infer_map_type(img.name)
            if map_type:
                found_maps.add(map_type)

            if not is_node_connected(node):
                report.append((f"[{mat.name}] Image node not connected", img.name, "WARNING"))

    for map_type in required_maps:
        if map_type not in found_maps:
            if map_type == "Roughness":
                level = "ERROR" if is_hero_asset else "WARNING"
                report.append((f"Missing Texture Map: {map_type}", "Not found", level))
            else:
                report.append((f"Missing Texture Map: {map_type}", "Not found", "ERROR"))

    missing_optional = [m for m in optional_maps if m not in found_maps]
    if missing_optional:
        report.append((f"Optional Maps", "Missing: " + ", ".join(missing_optional), "WARNING"))

    if found_maps:
        summary = ", ".join(sorted(found_maps))
        report.append(("Found Texture Maps", summary, "INFO"))

    return report

def check_rigging(obj):
    report = []

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    if obj.type != 'ARMATURE':
        report.append(("Rigging Check", "Not an armature object", "INFO"))
        return report

    bones = obj.data.bones
    pose_bones = obj.pose.bones if obj.pose else []

    bone_names_ok = all(b.name.isidentifier() for b in bones)
    hierarchy_ok = all(b.parent != b for b in bones if b.parent)

    report.append(("Bone Naming OK", str(bone_names_ok), "ERROR" if not bone_names_ok else "INFO"))
    report.append(("Hierarchy Clean", str(hierarchy_ok), "ERROR" if not hierarchy_ok else "INFO"))

    bone_count = len(bones)
    report.append(("Bone Count", str(bone_count), "INFO" if bone_count > 0 else "ERROR"))

    allowed_prefixes = ("DEF-", "CTRL-", "MCH-", "VIS-", "TGT-")
    non_conforming = [b.name for b in bones if not b.name.startswith(allowed_prefixes)]
    if non_conforming:
        report.append(("Naming Convention", f"{len(non_conforming)} bones not using DEF-/CTRL-/VIS-/TGT-", "ERROR"))

    blacklist_patterns = {"Bone*", "Joint*", "Temp*", "Unnamed*", "Helper*"}
    blacklisted = [b.name for b in bones if any(fnmatch.fnmatch(b.name, pattern) for pattern in blacklist_patterns)]

    if blacklisted:
        report.append(("Blacklisted Bone Names", ", ".join(blacklisted), "ERROR"))

    mesh_objs = [
        o for o in bpy.data.objects
        if o.type == 'MESH' and any(
            m.type == 'ARMATURE' and m.object == obj for m in o.modifiers
        )
    ]

    for mesh in mesh_objs:
        unassigned = sum(1 for v in mesh.data.vertices if not v.groups)
        report.append((f"{mesh.name} - Unassigned Verts", str(unassigned), "INFO" if unassigned == 0 else "ERROR"))

    has_constraints = any(c for b in obj.pose.bones for c in b.constraints)
    has_drivers = bool(obj.animation_data and obj.animation_data.drivers)
    report.append(("Constraints Present", str(has_constraints), "INFO" if not has_constraints else "WARNING"))
    report.append(("Drivers Present", str(has_drivers), "INFO" if not has_drivers else "WARNING"))

    return report
