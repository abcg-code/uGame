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

def update_scan_mode(self, context):
    mode = self.scan_mode
    self.scan_single_object = (mode == 'SINGLE')
    self.scan_selected_collection = (mode == 'COLLECTION')
    self.scan_entire_file = (mode == 'FILE')

class uGameSettings(bpy.types.PropertyGroup):
    scan_mode: bpy.props.EnumProperty(
        name="Scan Type",
        description="Choose what to scan",
        items=[
            ('SINGLE', "Active Object", "Scan only the active object"),
            ('COLLECTION', "Selected Collection", "Scan only the selected collection"),
            ('FILE', "Entire File", "Scan all objects in the file"),
        ],
        default='SINGLE',
        update=update_scan_mode
    )

    scan_single_object: bpy.props.BoolProperty(default=True)
    scan_selected_collection: bpy.props.BoolProperty(default=False)
    scan_entire_file: bpy.props.BoolProperty(default=False)

    exclude_highpoly: bpy.props.BoolProperty(
        name="Exclude High-Poly",
        description="Skip objects named *_high or in 'high poly' collections",
        default=True
    )
    aaa_game_check: bpy.props.BoolProperty(
        name="AAA Game Check",
        description="Use stricter texel density threshold and texture naming for AAA assets",
        default=False
    )
    is_hero_asset: bpy.props.BoolProperty(
        name="Hero Asset",
        description="Enable Stricter checks for hero-level assets",
        default=False
    )
    selected_collection: bpy.props.PointerProperty(
        name="Collection to Scan",
        type=bpy.types.Collection,
        description="CHOOSE which collection to scan for game-readiness"
    )
    asset_collection_mode: bpy.props.BoolProperty(
        name="Asset Collection Mode",
        description="Ignore object location errors for modular or grouped assets",
        default=False
    )

def register():
    bpy.utils.register_class(uGameSettings)
    bpy.types.Scene.ugame_settings = bpy.props.PointerProperty(type=uGameSettings)

def unregister():
    del bpy.types.Scene.ugame_settings
    bpy.utils.unregister_class(uGameSettings)