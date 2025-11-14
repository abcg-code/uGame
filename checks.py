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
from collections import defaultdict
from .helpers import (
    is_location_applied,
    get_top_parent,
    get_island_texel_densities,
    get_uv_utilization,
    get_all_objects_recursive,
    count_uv_islands,
    get_total_uv_and_face_area,
    is_uv_layout_stacked
)
from .constants import (
    required_maps,
    optional_maps,
    allowed_prefixes,
    blacklist_patterns,
    TEXEL_DENSITY_RANGE,
    TEXEL_DENSITY_MIN_AAA,
    TEXEL_DENSITY_DEVIATION_THRESHOLD,
)
from .texture_checks import (
    check_texture_naming,
    check_texture_resolution,
    is_node_connected,
    get_clean_map_type
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

    unapplied_types = set()

    for obj in objects:
        top = get_top_parent(obj)
        if not all(val == 1.0 for val in top.scale):
            unapplied_types.add("Scale")
        if not all(val == 0.0 for val in top.rotation_euler):
            unapplied_types.add("Rotation")
        if not is_location_applied(top):
            unapplied_types.add("Location")
        
    if unapplied_types:
        report.append(("Unapplied Transforms", f"{', '.join(sorted(unapplied_types))}", "ERROR"))
    else:
        report.append(("Transforms Applied", "OK", "INFO"))

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
        return [("UVs", "Not a mesh object", "INFO")]

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    settings = bpy.context.scene.ugame_settings
    mesh = obj.data
    aaa_mode = settings.aaa_game_check
    target = 90.0 if aaa_mode else 80.0
    pass_threshold = 85.0 if aaa_mode else 70.0

    uv_unwrapped = bool(mesh.uv_layers)
    seams_exist = any(edge.use_seam for edge in mesh.edges)

    # Unwrap/seams
    if not uv_unwrapped:
        report.append(("UVs", "Mesh not unwrapped", "ERROR"))
    else:
        report.append(("UV Unwrapped", "True", "INFO"))

    if not seams_exist:
        report.append(("Marked Seams", "None", "ERROR"))
    else:
        report.append(("Marked Seams", "Found", "INFO"))

    if not mesh.uv_layers.active:
        report.append(("UV Layer", "No active UV layer found", "ERROR"))
        return report

    # Islands
    uv_islands = count_uv_islands(obj)
    is_simple_mesh = len(mesh.polygons) < 100 and len(mesh.vertices) < 150
    if uv_islands == 1 and is_simple_mesh:
        report.append(("UV Island Count", f"{uv_islands} island (simple mesh)", "INFO"))
    else:
        threshold = 200 if settings.is_hero_asset else 100
        if uv_islands > threshold:
            report.append(("UV Island Count", f"{uv_islands} islands", "ERROR"))
        elif uv_islands > threshold * 0.75:
            report.append(("UV Island Count", f"{uv_islands} islands", "WARNING"))
        else:
            report.append(("UV Island Count", f"{uv_islands} islands", "INFO"))

    # Utilization
    utilization, overflow, uvs = get_uv_utilization(obj)
    if utilization == 0.0 and len(uvs) > 0:
        report.append(("UV Space Utilization", "UVs exist, but layout collapsed/invalid", "WARNING"))
    elif overflow:
        report.append(("UV Space Utilization", f"{utilization}% (UVs exceed 0-1 space)", "ERROR"))
    elif utilization >= pass_threshold:
        report.append(("Uv Space Utilization", f"{utilization}%", "INFO"))
    elif utilization >= target -5:
        report.append(("UV Space Utilization", f"{utilization}% (suboptimal)", "WARNING"))
    else:
        report.append(("UV Space Utilization", f"{utilization}% (too low)", "ERROR"))

    # Color atlas detection
    texture_map_names = [slot.name for slot in obj.material_slots if slot.material]
    has_normal = "Normal" in texture_map_names
    has_roughness = "Roughness" in texture_map_names

    atlas_score = 0
    if utilization < 15.0: atlas_score += 1
    unique_uvs = set((round(u, 5), round(v, 5)) for u, v in uvs) if uvs else set()
    unique_ratio = len(unique_uvs) / len(uvs) if uvs else 0
    if unique_ratio < 0.1: atlas_score += 1
    if not has_normal: atlas_score += 1
    if not has_roughness: atlas_score += 1
    if uv_islands < 15: atlas_score += 1
    if not seams_exist: atlas_score += 1

    is_color_atlas = atlas_score >= 5
    if is_color_atlas:
        report.append(("UV Strategy", f"Color atlas confidence: {atlas_score}/6", "INFO"))

    # Texel density
    if uv_unwrapped and not is_color_atlas:
        total_uv_area, total_face_area = get_total_uv_and_face_area(obj)
        ratio = round(total_uv_area / total_face_area, 2) if total_face_area > 0 else 0
        avg_density, deviation = get_island_texel_densities(obj)

        passed = ratio >= TEXEL_DENSITY_MIN_AAA if aaa_mode else TEXEL_DENSITY_RANGE[0] <= ratio <= TEXEL_DENSITY_RANGE[1]
        report.append(("Texel Density Ratio", f"{ratio:.2f} px/cm", "INFO" if passed else "WARNING"))
        report.append(("Texel Density Avg", f"{avg_density:.2f}", "INFO"))
        report.append(("Texel Density Deviation", f"{deviation:.2f}", "WARNING" if deviation > TEXEL_DENSITY_DEVIATION_THRESHOLD * avg_density else "INFO"))

        if is_uv_layout_stacked(uvs):
            level = "ERROR" if settings.is_hero_asset else "WARNING"
            report.append(("UV Layout", "Majority of UVs are stacked or overlapping", level))

        # Smart UV detection
        smart_uv = uv_islands > 50 and not seams_exist
        poor_density = ratio < 0.5 or deviation > TEXEL_DENSITY_DEVIATION_THRESHOLD * avg_density
        level = "ERROR" if settings.is_hero_asset else "WARNING"

        if smart_uv and poor_density:
            report.append(("Unwrapping Quality", "Likely Smart UV Project with poor texel density", level))
        elif smart_uv:
            report.append(("Unwrapping Quality", "Likely Smart UV Project", level))
        elif uv_islands < 2:
            report.append(("Unwrapping Quality", "Likely default UVs", "ERROR"))
        else:
            report.append(("Unwrapping Quality", "Seams detected, unwrap appears manual", "INFO"))

    if aaa_mode:
        report.append(("AAA Target", "UV Utilization should be ~90%", "INFO"))

    return report

def check_textures(obj, is_color_atlas=False):
    report = []
    used_images = set()
    found_maps = set()
    settings = bpy.context.scene.ugame_settings
    strict = settings.aaa_game_check
    is_hero_asset = settings.is_hero_asset

    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if not mat or not mat.use_nodes:
            continue

        for node in mat.node_tree.nodes:
            if node.type != 'TEX_IMAGE' or not node.image:
                continue

            img = node.image
            used_images.add(img)

            for check_fn in [check_texture_naming, check_texture_resolution]:
                arg = strict if check_fn != check_texture_resolution else is_hero_asset
                for label, value, level in check_fn(img, arg):
                    report.append((f"[{img.name}] {label}", "", level))
            
            if img.source == 'TILED':
                tile_count = len(img.tiles)
                report.append((f"[{mat.name}] UDIM detected", f"{tile_count} tiles", "INFO"))

            map_type = get_clean_map_type(img)
            if map_type:
                found_maps.add(map_type)

            if not is_node_connected(node):
                report.append((f"[{mat.name}] Image node not connected", img.name, "WARNING"))

    if not is_color_atlas:
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

    if obj.type != 'MESH':
        return [("Rigging", "Not a mesh object", "INFO")]

    armature_mod = next((m for m in obj.modifiers if m.type == 'ARMATURE'), None)
    if not armature_mod or not armature_mod.object:
        return [("Rigging", "No armature linked", "INFO")]

    armature = armature_mod.object
    bones = armature.data.bones
    pose_bones = armature.pose.bones if armature.pose else []

    bone_count = len(bones)
    report.append(("Bone Count", str(bone_count), "INFO" if bone_count > 0 else "ERROR"))

    non_conforming = [b.name for b in bones if not b.name.startswith(allowed_prefixes)]   
    blacklisted = [b.name for b in bones if any(fnmatch.fnmatch(b.name, pattern) for pattern in blacklist_patterns)]

    naming_issues = []
    if blacklisted:
        naming_issues.append(f"Blacklisted: {', '.join(blacklisted)}")
    if non_conforming:
        naming_issues.append(f"Missing prefix: {len(non_conforming)} bones")

    if naming_issues:
        report.append(("Bone Naming", ", ".join(naming_issues), "ERROR"))
    else:
        report.append(("Bone Naming", "OK", "INFO"))

    hierarchy_ok = all(b.parent != b for b in bones if b.parent)
    report.append(("Hierarchy Clean", str(hierarchy_ok), "ERROR" if not hierarchy_ok else "INFO"))

    unassigned = sum(1 for v in obj.data.vertices if not v.groups)
    report.append((f"{obj.name} - Unassigned Verts", str(unassigned), "INFO" if unassigned == 0 else "ERROR"))

    has_constraints = any(c for b in pose_bones for c in b.constraints)
    has_drivers = bool(armature.animation_data and armature.animation_data.drivers)
    report.append(("Constraints Present", str(has_constraints), "INFO" if not has_constraints else "WARNING"))
    report.append(("Drivers Present", str(has_drivers), "INFO" if not has_drivers else "WARNING"))

    return report

