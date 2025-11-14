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
from collections import defaultdict
from .checks import (
    check_collection_structure,
    check_collection_transforms
)
from .constants import (
    section_aliases
)

from .utils import (
    get_collection_uv_utilization
)
from .helpers import (
    dispatch_checks,
    infer_section_from_label
)
from .texture_checks import (
    get_clean_map_type,
    get_clean_name
)
def normalize_section(section):
    return section_aliases.get(section, section)

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

    for label, value, level in items:
        if level != "ERROR":
            continue

        reason = label
        if "]" in reason:
            reason = reason.split("]")[-1].strip()
        if reason.endswith(":"):
            reason = reason[:-1].strip()

        
        filename = value if value else label
        fake_img = type("FakeImg", (), {"name": filename})()
        map_type = get_clean_map_type(fake_img)
        if not map_type:
            map_type = get_clean_name(fake_img)
        
        grouped.setdefault(reason, []).append(map_type)
        total_maps += 1

    summaries = []
    for reason, maps in grouped.items():
        summaries.append(f"{reason}: {', '.join(sorted(set(maps)))}")
    return summaries, total_maps

def build_final_summary(report_data, width=150, collection_utilization=None,
                        asset_collection_mode=False, active_object_mode=False,
                        scan_single=False, scan_collection=False, scan_file=False):
    summary_lines = []
    multi_object_asset = len(report_data) > 1 and not asset_collection_mode and not active_object_mode

    settings = bpy.context.scene.ugame_settings
    aaa_mode = settings.aaa_game_check
    target = 90.0 if aaa_mode else 80.0
    pass_threshold = 85.0 if aaa_mode else 70.0

    if multi_object_asset and (scan_collection or scan_file):
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
            if status in ("WARNING", "FAIL"):
                summary_lines.append(
                    f"ASSET  : {settings.selected_collection.name if settings.selected_collection else 'File'} "
                    f"| [UVs], {status} ({uv_status})"
                )

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

        for obj_name, issues in report_data.items():
            for section, items in issues.items():
                if section == "UVs":
                    continue
                errors = extract_errors(items, group_by_label=True if section == "Modifiers" else False)
                if not errors:
                    continue

                if section == "Modifiers":
                    if not errors:
                        continue
                    disallowed = []
                    for label in errors:
                        clean = label.replace("Modifier:", "").replace("Modifiers:", "")
                        clean = clean.replace("(Disallowed type:", "").replace(")", "")
                        clean = clean.strip()
                        parts = [p.strip() for p in clean.split(":") if p.strip()]
                        if len(parts) > 1:
                            clean = parts[0]
                        elif parts:
                            clean = parts[0]
                        disallowed.append(clean)
                    section_text = f"[{section} ({len(errors)})], Disallowed type: {', '.join(disallowed)}"
                    
                elif section == "Textures":
                    if not errors:
                        continue
                    summaries, total_maps = summarize_texture_errors(items)
                    if summaries:
                        section_text = f"[{section} ({total_maps})], " + " | ".join(summaries)
                        summary_lines.append(f"OBJECT : {obj_name.ljust(12)} | {section_text}")
                else:
                    section_text = f"[{section} ({len(errors)})], {', '.join(errors)}"
                    summary_lines.append(f"OBJECT : {obj_name.ljust(12)} | {section_text}")

    else:
        for obj_name, issues in report_data.items():
            for section, items in issues.items():
                errors = extract_errors(items, group_by_label=True if section == "Modifiers" else False)
                if not errors and section != "Modifiers" and section != "Textures":
                    continue

                if section == "Modifiers":
                    if not errors:
                        continue
                    disallowed = []
                    for label in errors:
                        clean = label.replace("Modifier:", "").replace("Modifiers:", "")
                        clean = clean.replace("(Disallowed type:", "").replace(")", "")
                        clean = clean.strip()
                        parts = [p.strip() for p in clean.split(":") if p.strip()]
                        if len(parts) > 1:
                            clean = parts[0]
                        elif parts:
                            clean = parts[0]
                        disallowed.append(clean)
                    section_text = f"[{section} ({len(errors)})], Disallowed type: {', '.join(disallowed)}"
                elif section == "Textures":
                    if not errors:
                        continue
                    summaries, total_maps = summarize_texture_errors(items)
                    if summaries:
                        section_text = f"[{section} ({total_maps})], " + " | ".join(summaries)
                        summary_lines.append(f"OBJECT : {obj_name.ljust(12)} | {section_text}")
                else:
                    section_text = f"[{section} ({len(errors)})], {', '.join(errors)}"
                    summary_lines.append(f"OBJECT : {obj_name.ljust(12)} | {section_text}")
    
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
    lines.append(f"\n{'=' * len(header)}\n{header}\n{'=' * len(header)}\n")

    normalized_sections = defaultdict(list)
    for raw_section, items in obj_sections.items():
        normalized = normalize_section(raw_section)
        normalized_sections[normalized].extend(items)
    expected_sections = ["Geometry", "Textures", "UVs", "Modifiers", "Rigging"]

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

def report_has_errors(report_data):
    for obj_issues in report_data.values():
        for sectiion_issues in obj_issues.values():
            for _, _, level in sectiion_issues:
                if level == "ERROR":
                    return True
    return False