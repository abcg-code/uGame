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
from .utils import (
    is_high_poly,
    get_all_objects_in_collection,
    get_collection_uv_utilization
)
from .report_utils import (
    collect_report_data,
    build_final_summary,
    build_per_object_detail,
    open_report_in_new_window,
    format_collection_block,
    report_has_errors,
    normalize_section
)
from .helpers import (
    dispatch_checks,
    infer_section_from_label
)
from collections import defaultdict

class OBJECT_OT_CheckGameReady(bpy.types.Operator):
    bl_idname = "object.check_game_ready"
    bl_label = "Check Game-Ready Status"
    bl_category = "uGame"
    bl_description = "Check mesh and armature objects for game-readiness"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        report_lines = []
        settings = context.scene.ugame_settings
        if settings.scan_selected_collection and not settings.selected_collection:
            self.report({'WARNING'}, "Please select a collection to scan.")
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        scan_single = settings.scan_single_object
        scan_collection = settings.scan_selected_collection
        scan_file = settings.scan_entire_file
        
        is_hero_asset = settings.is_hero_asset
        exclude_highpoly = settings.exclude_highpoly
        aaa_mode = settings.aaa_game_check
        selected_collection = settings.selected_collection
        
        excluded_objects = []
        objects_to_check = []

        if scan_single:
            obj = context.active_object
            if obj and obj.type in {'MESH', 'ARMATURE'}:
                if exclude_highpoly and is_high_poly(obj):
                    excluded_objects.append(obj.name)
                else:
                    objects_to_check = [obj]
            else:
                self.report({'WARNING'}, "No valid active object selected.")
                context.window_manager.modal_handler_add(self)
                return {'RUNNING_MODAL'}

        elif scan_file:
            all_objects = [obj for obj in bpy.data.objects if obj.type in {'MESH', 'ARMATURE'}]
            for obj in all_objects:
                if exclude_highpoly and is_high_poly(obj):
                    excluded_objects.append(obj.name)
                else:
                    objects_to_check.append(obj)

        elif scan_collection:
            if not selected_collection:
                self.report({'WARNING'}, "Please select a collection to scan.")
                context.window_manager.modal_handler_add(self)
                return {'RUNNING_MODAL'}

            all_objects = get_all_objects_in_collection(selected_collection)
            for obj in all_objects:
                if obj.type in {'MESH', 'ARMATURE'}:
                    if exclude_highpoly and is_high_poly(obj):
                        excluded_objects.append(obj.name)
                    else:
                        objects_to_check.append(obj)

        else:
            self.report({'WARNING'}, "No scan mode selected.")
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        if not objects_to_check:
            self.report({'WARNING'}, "No valid objects found to scan.")
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        mesh_objects = [obj for obj in objects_to_check if obj.type == 'MESH']
        report_data = collect_report_data(mesh_objects, settings)

        collection_utilization = None
        if scan_collection and selected_collection:
            uv_report = get_collection_uv_utilization(selected_collection)
            for label, value, level in uv_report:
                if "UV Space Utilization" in label and value:
                    try:
                        collection_utilization = float(str(value).strip("%"))
                    except:
                        pass

        final_summary_text = build_final_summary(
            report_data,
            collection_utilization=collection_utilization,
            asset_collection_mode=settings.asset_collection_mode,
            active_object_mode=scan_single,
            scan_collection=scan_collection,
            scan_file=scan_file,
            sel=selected_collection
        )

        # Report Header
        title = "Game-Ready Check Report"
        report_lines.append(f"\n{title}\n{'=' * len(title)}\n\n")
        report_lines.append(f"Asset Type: {'Hero' if is_hero_asset else 'Background'}\n")
        if scan_single:
            scope_label = "Active Object Scan"
        elif scan_file:
            scope_label = "Full File Scan"
        elif scan_collection:
            scope_label = "Nested Collection Scan" if selected_collection.children else "Single Collection Scan"
        else:
            scope_label = "Unknown Scan Scope"

        report_lines.append(f"Scope: {scope_label}\n")

        # Final Summary
        title = "[FINAL SUMMARY]"
        report_lines.append(f"\n\n{'=' * len(title)}\n{title}\n{'=' * len(title)}\n\n")
        has_errors = report_has_errors(report_data, asset_collection_mode=settings.asset_collection_mode, active_object_mode=scan_single)
        if has_errors:
            report_lines.append("Overall Game-Ready Status: FAIL\n\n")
        else:
            report_lines.append("Overall Game-Ready Status: PASS")

        report_lines.append(final_summary_text + "\n")
            

        # Excluded Objects
        title = "[Excluded Objects]"
        if excluded_objects:
            report_lines.append(f"\n\n{'=' * len(title)}\n{title}\n{'=' * len(title)}\n\n")
            for name in excluded_objects:
                report_lines.append(f"- {name} (high-poly)\n")

        # Collection Structure
        title = "[Collection Structure]"
        if scan_collection and selected_collection:
            report_lines.append(f"\n\n{'=' * len(title)}\n{title}\n{'=' * len(title)}\n\n")
            report_lines.extend(format_collection_block(selected_collection))
            for child in selected_collection.children:
                report_lines.append("\n")
                report_lines.extend(format_collection_block(child))

        # Per-object detail
        title = "[Per-Object Detail]"
        report_lines.append(f"\n\n{'=' * len(title)}\n{title}\n{'=' * len(title)}\n")
        settings = context.scene.ugame_settings
        for obj in mesh_objects:
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

            obj_sections = dict(sectioned)
            report_lines.extend(build_per_object_detail(obj.name, obj_sections, settings))

        # Output
        report_text = "".join(report_lines)
        open_report_in_new_window(report_text)
        self.report({'INFO'}, "Game-Ready report opened in new Text Editor window")
        return {'FINISHED'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            return {'CANCELLED'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            result = self.execute(context)
            if result == {'FINISHED'}:
                return {'FINISHED'}
            return {'RUNNING_MODAL'}
        return {'RUNNING_MODAL'}

def register():
    bpy.utils.register_class(OBJECT_OT_CheckGameReady)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_CheckGameReady)
