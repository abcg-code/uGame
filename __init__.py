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

bl_info = {
    "name": "uGame",
    "author": "Adrian Bellworthy",
    "version": (1, 0, 7),
    "blender": (4, 5, 0),
    "location": "Topbar",
    "description": "Checks models for game-readiness with customizable settings",
    "category": "3D View"
}

from . import main

def register():
    main.register()

def unregister():
    main.unregister()

