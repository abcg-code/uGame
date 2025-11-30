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
import os
import re
from collections import defaultdict
from .checks import (
    check_collection_structure,
    check_collection_transforms
)
from .constants import (
    section_aliases
)

from .utils import (
    get_collection_uv_utilization,
)
from .helpers import (
    dispatch_checks,
    infer_section_from_label,
    has_uvs,
    has_seams,
    ensure_object_mode,
    is_mesh,
    has_armature,
    collection_has_armature,
    aaa_mode,
    is_multi_object_asset
)
from .texture_checks import (
    get_clean_map_type,
    get_clean_name
)
def normalize_section(section: str) -> str:
    cleaned = section.strip().rstrip(":")
    cleaned = re.sub(r"\s*\(.*\)$", "", cleaned)
    if cleaned in section_aliases:
        return section_aliases[cleaned]
    for key, alias in section_aliases.items():
        if cleaned.startswith(key) or key in cleaned:
            return alias
    return section

def build_asset_summary_line(category, issues, status="FAIL", width=150):
    prefix = f"ASSET : {category} | {status} ("
    indent = " " * len(prefix)
    lines = []
    line = prefix
    current_length = len(line)

    for i, issue in enumerate(issues):
        issue_text = issue + (", " if i < len(issues) - 1 else "")
        if current_length + len(issue_text) > width:
            lines.append(line.rstrip(", "))
            line = indent + issue_text
            current_length = len(line)
        else:
            line += issue_text
            current_length += len(issue_text)

    line += ")"
    lines.append(line)
    return lines

def format_error(label, value):
    return f"{label} ({value})" if value and value != "None found" else label

def extract_errors(section_items, group_by_label=False, prefix_filter=None):
    grouped = defaultdict(list)
    results = []
    for label, value, level in section_items:
        if level == "ERROR" and (not prefix_filter or label.startswith(prefix_filter)):
            if group_by_label:
                grouped[label].append(value)
            else:
                results.append(format_error(label, value))
    if group_by_label:
        return [f"{label}: ({', '.join(sorted(set(values)))})" for label, values in grouped.items()]
    return sorted(results)

def collect_report_data(objects, settings):
    report_data = {}
    for obj in objects:
        flat_report = dispatch_checks(obj, settings)
        sectioned = defaultdict(list)

        for item in flat_report:
            if isinstance(item, tuple) and len(item) == 3:
                label, value, level = item
                raw_section = infer_section_from_label(label)
                section = normalize_section(raw_section)
                sectioned[section].append((label, value, level))
            else:
                sectioned["Other"].append(item)
        report_data[obj.name] = dict(sectioned)
    return report_data

def summarize_texture_errors(items):
    grouped = {}
    total_maps = 0

    for reason, map_name, level in items:
        if level != "ERROR":
            continue
        grouped.setdefault(reason, []).append(map_name)
        total_maps += 1

    order = [
        "Missing Texture Map",
        "Texture name invalid",
        "Contains disallowed term",
        "Missing required suffix",
        "Not power-of-two",
        "Resolution too high for background asset",
        "Resolution too low for Hero Asset",
        "Very low resolution"
    ]

    summaries = []
    for reason in order:
        if reason in grouped:
            maps = grouped[reason]
            summaries.append(f"{reason}: {', '.join(sorted(set(maps)))}")

    for reason, maps in grouped.items():
        if reason not in order:
            summaries.append(f"{reason}: {', '.join(sorted(set(maps)))}")

    return summaries, total_maps

def build_final_summary(report_data,
                        asset_collection_mode=False,
                        active_object_mode=False,
                        scan_collection=False,
                        scan_file=False,
                        collection_utilization=None,
                        sel=None,
                        width=100):
    summary_lines = []
    target = 90.0 if aaa_mode() else 80.0
    pass_threshold = 85.0 if aaa_mode() else 70.0
    multi = is_multi_object_asset(report_data, asset_collection_mode, active_object_mode)

    def format_section(section, errors, width, indent):
        lines = []
        prefix = f"[{section} ({len(errors)})], "
        current_line = indent + prefix
        current_length = len(current_line)
        for i, err in enumerate(errors):
            err_text = err + (", " if i < len(errors) - 1 else "")
            if current_length + len(err_text) > width:
                lines.append(current_line.rstrip(", "))
                current_line = indent + err_text
                current_length = len(current_line)
            else:
                current_line += err_text
                current_length += len(err_text)
        lines.append(current_line.rstrip(", "))
        return lines

    def wrap_texture_summary(summary, indent, width):
        lines = []
        parts = summary.split(":")
        if len(parts) == 2:
            prefix, names_str = parts
            names = [n.strip() for n in names_str.split(",")]
            current_line = prefix + ":"
            for name in names:
                token = name + ","
                if len(current_line) + len(token) > width:
                    lines.append(current_line.rstrip(","))
                    current_line = indent + token
                else:
                    current_line += " " + token
            lines.append(current_line.rstrip(","))
        else:
            lines.append(summary)
        return lines

    if multi and (scan_collection or scan_file):
        if collection_utilization is not None:
            if collection_utilization >= pass_threshold:
                uv_status = f"UV Space Utilization (Collection: {collection_utilization:.2f}%)"
                status = "PASS"
            elif collection_utilization >= target - 5:
                uv_status = f"UV Space Utilization (Collection: {collection_utilization:.2f}% (suboptimal))"
                status = "WARNING"
            else:
                uv_status = f"UV Space Utilization (Collection: {collection_utilization:.2f}% (too low))"
                status = "FAIL"
            summary_lines.append(f"ASSET : UVs | {uv_status} [{status}]")

        consolidated_textures = []
        for issues in report_data.values():
            if "Textures" not in issues:
                continue
            missing_maps = extract_errors(
                issues["Textures"], group_by_label=True, prefix_filter="Missing Texture Map:"
            )
            consolidated_textures.extend(missing_maps)
        if consolidated_textures:
            summary_lines.extend(build_asset_summary_line("Textures", consolidated_textures, width=width))
        
        summary_lines.append("")

    for obj_name, issues in report_data.items():
        summary_lines.append(f"OBJECT : {obj_name}")
        indent = " " * 8

        for section, items in issues.items():
            errors = extract_errors(items, group_by_label=True if section == "Modifiers" else False)
            if not errors and section not in ("Modifiers", "Textures"):
                continue

            if section == "Modifiers":
                if errors:
                    disallowed = []
                    for label in errors:
                        clean = label.replace("Modifier:", "").replace("Modifiers:", "")
                        clean = clean.replace("(Disallowed type:", "").replace(")", "").strip()
                        parts = [p.strip() for p in clean.split(":") if p.strip()]
                        clean = parts[0] if parts else clean
                        disallowed.append(clean)
                    section_text = f"[{section} ({len(errors)})], Disallowed type: {', '.join(disallowed)}"
                    summary_lines.append(indent + section_text)
                    
            elif section == "Textures":
                if errors:
                    summaries, total_maps = summarize_texture_errors(items)
                    if summaries:
                        prefix = f"[Textures ({total_maps})], "
                        for i, summary in enumerate(summaries):
                            wrapped_lines = wrap_texture_summary(summary, indent, width)
                            if i == 0:
                                summary_lines.append(indent + prefix + wrapped_lines[0])
                                for line in wrapped_lines[1:]:
                                    summary_lines.append(indent + line)
                            else:
                                for line in wrapped_lines:
                                    summary_lines.append(indent + line)
            else:
                if errors:
                    summary_lines.extend(format_section(section, errors, width, indent))
        
        summary_lines.append("")
    
    return "\n".join(summary_lines)

def build_detailed_report(objects):
    lines = ["\n\n[Per-Object Detail]\n==================="]
    for obj in objects:
        flat_report = dispatch_checks(obj, bpy.context.scene.ugame_settings)
        sectioned = defaultdict(list)
        for item in flat_report:
            if isinstance(item, tuple) and len(item) == 3:
                label, value, level = item
                raw_section = infer_section_from_label(label)
                section = normalize_section(raw_section)
                sectioned[section].append((label, value, level))
            else:
                sectioned["Other"].append(item)
        obj_sections = dict(sectioned)
        detail_lines = build_per_object_detail(obj.name, obj_sections)
        lines.extend(detail_lines)
    return "\n".join(lines)

def build_per_object_detail(obj_name, obj_sections, settings=None):
    lines = []
    header = f"Object: {obj_name}"
    lines.append(f"\n{header}\n{'=' * len(header)}\n")

    normalized_sections = defaultdict(list)
    for raw_section, items in obj_sections.items():
        normalized = normalize_section(raw_section)
        normalized_sections[normalized].extend(items)
    expected_sections = ["Geometry", "Modifiers", "Rigging", "UVs", "Textures"]

    for section in expected_sections:
        items = normalized_sections.get(section, [])
        lines.append(f"\n[{section}]\n{'-' * len(section) + '--'}\n")

        if not items:
            lines.append(f"[INFO] No data returned for {section} - check may not apply to this object\n")
            lines.append(f"[SUMMARY] {section}: PASS\n")
            continue

        section_errors = []
        section_warnings = []

        for item in items:
            if isinstance(item, tuple) and len(item) == 3:
                label, value, level = item
                lines.append(f"[{level}] {label}: {value}\n")
                if level == "ERROR":
                    section_errors.append(str(label))
                elif level == "WARNING":
                    section_warnings.append(str(label))
            elif isinstance(item, str):
                lines.append(f"[INFO] {item}\n")
            else:
                lines.append(f"[INFO] Malformed report item: {item}\n")

        cleaned_errors = []
        for label in section_errors:
            if label.startswith("Missing Texture Map: "):
                cleaned_errors.append(label.replace("Missing Texture Map: ", ""))
            else:
                cleaned_errors.append(label)
        
        if cleaned_errors:
            for line in build_asset_summary_line(section, sorted(set(cleaned_errors))):
                lines.append(line + "\n")
        else:
            summary = f"[SUMMARY] {section}: PASS"
            if section_warnings:
                summary += " - With Warnings"
            lines.append(summary + "\n")

    return lines

def format_collection_block(collection):
    block = []
    block.append(f"[{collection.name}]\n{'-' * len(collection.name) + '--'}\n")

    structure = check_collection_structure(collection)
    transforms = check_collection_transforms(collection)
    uv_report = get_collection_uv_utilization(collection)

    for label, value, level in structure + transforms + uv_report:
        block.append(f"[{level}] {label}: {value}\n")
    
    return block

def open_report_in_new_window(report_text):
    bpy.ops.wm.window_new()
    wm = bpy.context.window_manager
    new_window = wm.windows[-1]
    area = next((a for a in new_window.screen.areas if a.type != 'TEXT_EDITOR'), None)
    if area:
        area.type = 'TEXT_EDITOR'
        space = area.spaces.active
        txt = bpy.data.texts.get("GameReadyReport") or bpy.data.texts.new("GameReadyReport")
        txt.clear()
        txt.write(report_text)

        space.text = txt
        space.top = 0
        space.show_syntax_highlight = False
    else:
        print("Could not find a suitable area to display the report")

def report_has_errors(report_data, asset_collection_mode=False, active_object_mode=False):
    multi = is_multi_object_asset(report_data, asset_collection_mode, active_object_mode)
    for obj_issues in report_data.values():
        for section, section_items in obj_issues.items():
            for label, value, level in section_items:
                if level == "ERROR":
                    if multi and section == "UVs" and "UV Space Utilization" in label:
                        continue
                    return True
    return False