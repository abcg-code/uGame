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
from . import icons

override_orig = None

def override_topbar():
    global override_orig

    if override_orig is None:
        override_orig = bpy.types.TOPBAR_HT_upper_bar.draw_left

    def new_draw_left(self, context):
        layout = self.layout
        row = layout.row(align=True)
        if icons.custom_icons and "gamepad" in icons.custom_icons:
            row.operator("object.game_ready_popup", text="", icon_value=icons.custom_icons["gamepad"].icon_id)
        else:
            row.operator("object.game_ready_popup", text="", icon='GHOST_ENABLED')
        if override_orig:
            override_orig(self, context)

    bpy.types.TOPBAR_HT_upper_bar.draw_left = new_draw_left

class OBJECT_OT_GameReadyPopup(bpy.types.Operator):
    bl_idname = "object.game_ready_popup"
    bl_label = "Game Ready Check"
    bl_description = "Check game-readiness with settings"
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        layout = self.layout
        layout.label(text="Check assets for game-readiness")
        settings = context.scene.ugame_settings

        box = layout.box()
        box.prop(settings, "exclude_highpoly")
        box.prop(settings, "asset_collection_mode")
        box.prop(settings, "aaa_game_check")
        box.prop(settings, "is_hero_asset", text="Hero Asset")
        box.prop(settings, "scan_mode")
        if settings.scan_selected_collection:
            box.prop(settings, "selected_collection")

    def execute(self, context):
        bpy.ops.object.check_game_ready()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

def draw_game_ready_button(self, context):
    layout = self.layout
    layout.separator()
    layout.operator("object.game_ready_popup", text="", icon='GHOST_ENABLED')

def register():
    bpy.utils.register_class(OBJECT_OT_GameReadyPopup)
    override_topbar()

def unregister():
    undo_override_topbar()
    bpy.utils.unregister_class(OBJECT_OT_GameReadyPopup)

def undo_override_topbar():
    global override_orig
    if override_orig:
        bpy.types.TOPBAR_HT_upper_bar.draw_left = override_orig
        override_orig = None
