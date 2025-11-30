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
from .constants import section_aliases
from mathutils import Vector

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
        area += abs((b - a).cross(c - a)) / 2.0

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
                uv_tuple = (uv.x, uv.y)
                uvs.append(uv_tuple)

                u, v = uv_tuple
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
    unique_uvs = set((round(u, 5), round(v, 5)) for u, v in uvs)
    return len(unique_uvs) / len(uvs) < threshold

def dispatch_checks(obj, settings):
    from .checks import (
        check_geometry,
        check_object_modifiers,
        check_uvs,
        check_textures,
        check_rigging
    )

    report = []

    if obj.type == 'ARMATURE':
        return []

    if obj.type == 'MESH':
        report.extend(check_geometry(obj, settings))
        report.extend(check_object_modifiers(obj))
        report.extend(check_uvs(obj, multi_object_asset=(not settings.scan_single_object)))
        report.extend(check_textures(obj))

        if has_armature(obj):
            report.extend(check_rigging(obj))

        return report

    return [("Other", f"Skipped unsupported type: {obj.type}", "INFO")]

def infer_section_from_label(label: str) -> str:
    for key, section in section_aliases.items():
        if label.startswith(key) or key in label:
            return section

    if (
        label.startswith("Texture")
        or label.startswith("Missing Texture Map")
        or label.startswith("Optional Maps")
        or label.startswith("Found Texture Maps")
        or "Resolution" in label
        or "power-of-two" in label
    ):
        return "Textures"

    if "Modifier" in label or label.startswith("Modifiers"):
        return "Modifiers"

    if "UV" in label or label.startswith("Texel") or label.startswith("Unwrapping"):
        return "UVs"

    if ("Bone" in label
        or "Rigging" in label
        or "Constraints" in label
        or "Drivers" in label
        or "Unassigned Verts" in label
    ):
        return "Rigging"
    
    if label in {
        "Vertex Count", "Face Count", "Edge Count", "N-gons", "Non-Manifold Edges",
        "Stray Vertices", "Transforms Applied", "Unapplied Transforms", "Normals", "Double Vertices"
    }:
        return "Geometry"
  
    return "Other"

def has_textures(obj) -> tuple[bool, int, list[tuple[str, str, str]]]:
    found = False
    packed_count = 0
    unpacked_reports = []

    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if not mat or not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                found = True
                img = node.image
                if img.packed_file is not None:
                    packed_count += 1 
                else:
                    unpacked_reports.append(("Textures", f"External texture image ({img.name})", "ERROR"))
    return found, packed_count, unpacked_reports

def ensure_object_mode():
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

def is_mesh(obj):
    return obj.type == 'MESH'

def has_armature(obj) -> bool:
    return any(mod.type == 'ARMATURE' and mod.object for mod in obj.modifiers)

def collection_has_armature(collection):
    return any(obj.type == 'ARMATURE' for obj in collection.objects)

def has_uvs(obj) -> bool:
    return obj.type == 'MESH' and bool(obj.data.uv_layers)

def has_seams(obj) -> bool:
    return obj.type == 'MESH' and any(edge.use_seam for edge in obj.data.edges)

def aaa_mode() -> bool:
    return bpy.context.scene.ugame_settings.aaa_game_check

def is_hero_asset() -> bool:
    return bpy.context.scene.ugame_settings.is_hero_asset

def is_multi_object_asset(report_data, asset_collection_mode, active_object_mode):
    return len(report_data) > 1 and not asset_collection_mode and not active_object_mode

# # *******************
# # * Flipped Normals *
# # *******************

# # -----------------------------
# # Utilities: islands and volume
# # -----------------------------

def _is_mesh(obj):
    return getattr(obj, "type", None) == "MESH"

def _island_faces(bm):
    islands = []
    visited = set()
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        if f.index in visited:
            continue
        stack = [f]
        island =[]
        while stack:
            face = stack.pop()
            if face.index in visited:
                continue
            visited.add(face.index)
            island.append(face)
            for e in face.edges:
                for lf in e.link_faces:
                    if lf.index not in visited:
                        stack.append(lf)
        islands.append(island)
    return islands

# # -------------------------
# # Seed selection per island
# # -------------------------

def _select_seed_face(island):
    verts = {v for f in island for v in f.verts}
    if not verts:
        return None
    centroid = sum((v.co for v in verts), Vector((0.0, 0.0, 0.0))) / len(verts)
    best, best_dot = None, -1.0
    for f in island:
        c = f.calc_center_median()
        outward = (c - centroid)
        if outward.length_squared == 0.0:
            continue
        outward.normalize()
        d = f.normal.dot(outward)
        if d > best_dot:
            best, best_dot = f, d
    return best

def _propagate_consistency(island, inside=False):
    flipped_local = set()
    bm_local = bmesh.new()
    vmap = {}
    for f in island:
        for v in f.verts:
            if v.index not in vmap:
                vmap[v.index] = bm_local.verts.new(v.co.copy())
    bm_local.verts.ensure_lookup_table()

    fmap = {}
    for f in island:
        new_face = bm_local.faces.new([vmap[v.index] for v in f.verts])
        fmap[f.index] = new_face
    bm_local.faces.ensure_lookup_table()
    bm_local.normal_update()

    adjacency = {f.index: set() for f in island}
    for f in island:
        for e in f.edges:
            if len(e.link_faces) == 2:
                f1, f2 = e.link_faces
                adjacency[f1.index].add(f2.index)
                adjacency[f2.index].add(f1.index)
    
    seed = _select_seed_face(island)
    if seed is None:
        bm_local.free()
        return flipped_local

    seed_local = fmap[seed.index]
    bm_local.faces.ensure_lookup_table()
    bm_local.normal_update()
    seed_normal = seed_local.normal.copy()

    if inside:
        seed_normal.negate()

    visited = set()
    stack = [seed.index]
    while stack:
        idx = stack.pop()
        if idx in visited:
            continue
        visited.add(idx)
        f_local = fmap[idx]

        if f_local.normal.dot(seed_normal) < 0:
            f_local.normal_flip()
            flipped_local.add(idx)
            bm_local.normal_update()

        for n_idx in adjacency[idx]:
            if n_idx not in visited:
                stack.append(n_idx)

    bm_local.free()
    return flipped_local

# # ------------------------------
# # Public API: find flipped faces
# # ------------------------------

def find_flipped_faces(obj, threshold=0.999):
    if getattr(obj, "type", None) != "MESH":
        return []

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.normal_update()

    current_status = {f.index: f.normal.copy() for f in bm.faces}

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()

    new_status = {f.index: f.normal.copy() for f in bm.faces}

    flipped = []
    for idx, orig_normal in current_status.items():
        dot = orig_normal.dot(new_status[idx])
        if dot < threshold:
            flipped.append(idx)

    bm.free()
    return flipped