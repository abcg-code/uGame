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
import textwrap
from collections import defaultdict
from .checks import (
    check_collection_structure,
    check_collection_transforms,
    check_geometry,
    check_textures,
    check_uvs,
    check_object_modifiers,
    check_rigging
)
from .constants import section_aliases
from .utils import (
    get_collection_uv_utilization,
    collect_object_sections
)

def build_section_summary_line(section, issue_labels, width=150):
    prefix = f"[SUMMARY] {section}: FAIL (Issues: "
    indent = " " * len(prefix)
    lines = []
    line = prefix
    current_length = len(line)

    for i, label in enumerate(issue_labels):
        label_text = label + (", " if i < len(issue_labels) - 1 else "")
        if current_length + len(label_text) > width:
            lines.append(line.rstrip(", "))
            line = indent + label_text
            current_length = len(line)
        else:
            line += label_text
            current_length += len(label_text)

    if current_length + 1 > width:
        lines.append(line.rstrip(", "))
        lines.append(indent + ")")
    else:
        line += ")"
        lines.append(line)
    return lines

def normalize_section(section):
    return section_aliases.get(section, section)

def extract_failures(obj_sections):
    failures = {}
    for section, items in obj_sections.items():
        normalized = normalize_section(section)
        for item in items:
            if len(item) == 3 and item[2] == "ERROR":
                if normalized == "Textures":
                    reason, texture_name, _ = item
                    failures.setdefault(normalized, []).append((reason, texture_name))
                else:
                    label, _, _ = item
                    failures.setdefault(normalized, []).append(str(label))
    
    return failures

def collect_report_data(objects, settings):
    report_data = {}

    for obj in objects:
        obj_name = obj.name
        report_data[obj_name] = {}

        geo = check_geometry(obj, settings)
        geo_issues = [item for item in geo if item[2] == "ERROR"]
        if geo_issues:
            report_data[obj_name]["Geometry"] = geo_issues

        tex = check_textures(obj)
        tex_issues = [item for item in tex if item[2] == "ERROR"]
        if tex_issues:
            report_data[obj_name]["Textures"] = tex_issues

        uvs = check_uvs(obj)
        uv_issues = [item for item in uvs if item[2] == "ERROR"]
        if uv_issues:
            report_data[obj_name]["UVs"] = uv_issues

        mod = check_object_modifiers(obj)
        mod_issues = [item for item in mod if item[2] == "ERROR"]
        if mod_issues:
            report_data[obj_name]["Modifiers"] = mod_issues

        rig = check_rigging(obj)
        rig_issues = [item for item in rig if item[2] == "ERROR"]
        if rig_issues:
            report_data[obj_name]["Rigging"] = rig_issues

    return report_data

def build_final_summary(report_data, width=150):
    summary_lines = []
    section_order = ["Geometry", "Texture", "Missing Texture Map", "UVs", "Modifiers", "Rigging"]

    for obj_name, issues in report_data.items():
        parts = []

        if "Geometry" in issues:
            geo_labels = sorted([
                f"{label.strip()} ({value})" if value and value != "None found" else label.strip()
                for label, value, level in issues["Geometry"]
                if level == "ERROR"
            ])
            if geo_labels:
                parts.append(("Geometry", geo_labels))

        if "Textures" in issues:
            texture_errors = defaultdict(list)
            for label, _, level in issues["Textures"]:
                if level == "ERROR" and not label.startswith("Missing Texture Map:"):
                    if label.startswith("[") and "]" in label:
                        tex_name = label.split("]")[0][1:]
                        tex_issue = label.split("]")[1].strip()
                        texture_errors[tex_name].append(tex_issue)

            tex_labels = [
                f"[{tex_name}] " + ", ".join(sorted(problems))
                for tex_name, problems in sorted(texture_errors.items())
            ]
            if tex_labels:
                parts.append(("Texture", tex_labels))

            missing_maps = sorted(set([
                label.split(": ")[-1]
                for label, _, level in issues["Textures"]
                if level == "ERROR" and label.startswith("Missing Texture Map:")
            ]))
            if missing_maps:
                parts.append((f"Missing Texture Map", (missing_maps)))

        if "UVs" in issues:
            uv_labels = sorted([label for label, _, _ in issues["UVs"]])
            parts.append(("UVs", uv_labels))

        if "Modifiers" in issues:
            mod_labels = sorted([label.replace("Modifier: ", "") for label, _, _ in issues["Modifiers"]])
            parts.append(("Modifiers", mod_labels))

        if "Rigging" in issues:
            rig_labels = sorted([label for label, _, _ in issues["Rigging"]])
            parts.append(("Rigging", rig_labels))

        if not parts:
            continue

        parts.sort(key=lambda x: section_order.index(x[0]) if x[0] in section_order else 99)
        
        prefix = f"- {obj_name}: "
        indent = " " * len(prefix)
        object_lines = []
        line = prefix
        current_length = len(line)

        for section_index, (section, labels) in enumerate(parts):
            labels = [label for label in labels if label.strip()]
            section_text = f"| [{section} ({len(labels)})] ["
            continuation_indent = indent + " " * len(section_text)

            if section_index > 0:
                object_lines.append(line.rstrip(", "))
                line = indent + section_text
                current_length = len(line)
            else:
                line += section_text
                current_length = len(section_text)

            for i, label in enumerate(labels):
                label_text = label + (", " if i < len(labels) -1 else "")
                if i == 0 or current_length + len(label_text) <= width:
                    line += label_text
                    current_length += len(label_text)
                else:
                    object_lines.append(line.rstrip(", "))
                    line = continuation_indent + label_text
                    current_length = len(line)

            line += "] "
            current_length += 1

        object_lines.append(line.rstrip(", "))
        summary_lines.extend(object_lines)
    
    return "\n".join(summary_lines)

def build_detailed_report(objects):
    lines = ["\n\n[Per-Object Detail]\n==================="]

    for obj in objects:
        obj_sections = collect_object_sections(obj)
        detail_lines = build_per_object_detail(obj.name, obj_sections)
        lines.extend(detail_lines)

    return "\n".join(lines)

def build_per_object_detail(obj_name, obj_sections, settings=None):
    lines = []
    header = f"Object: {obj_name}"
    lines.append(f"\n{'=' * len(header)}\n{header}\n{'=' * len(header)}\n")

    normalized_sections = {
        normalize_section(k): v for k, v in obj_sections.items()
    }

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
            for line in build_section_summary_line(section, sorted(set(cleaned_errors))):
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