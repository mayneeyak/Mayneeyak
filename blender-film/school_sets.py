"""School sets for NED: the school front, the hallway, a classroom and the playground.

Each builder takes the film and an origin (x, y) and returns a dict of useful spots
(positions in meters, already offset by the origin).
"""

import math

import bpy

from filmkit import props, shapes
from filmkit.materials import material


def _at(o, x, y, z=0.0):
    return (o[0] + x, o[1] + y, z)


def _area_light(film, name, location, size=(4, 2), energy=300, color=(1.0, 0.96, 0.9)):
    light = bpy.data.lights.new(name, "AREA")
    light.shape = "RECTANGLE"
    light.size, light.size_y = size
    light.energy = energy
    light.color = color
    obj = bpy.data.objects.new(name, light)
    film.collection.objects.link(obj)
    obj.location = location
    return obj


def _window(film, o, x, y, z, w=1.4, h=1.4, facing_y=True):
    frame = material("window_frame", "#f2efe8", 0.5)
    glass = material("window_glass", "#bfe0ff", 0.05, glow=0.6, coat=1.0)
    if facing_y:
        shapes.box(film, "WinFrame", (w + 0.16, 0.08, h + 0.16), _at(o, x, y, z), mat=frame)
        shapes.box(film, "WinGlass", (w, 0.1, h), _at(o, x, y - 0.01, z), mat=glass)
        shapes.box(film, "WinBar", (0.06, 0.11, h), _at(o, x, y - 0.02, z), mat=frame)
    else:
        shapes.box(film, "WinFrame", (0.08, w + 0.16, h + 0.16), _at(o, x, y, z), mat=frame)
        shapes.box(film, "WinGlass", (0.1, w, h), _at(o, x + 0.01, y, z), mat=glass)
        shapes.box(film, "WinBar", (0.11, 0.06, h), _at(o, x + 0.02, y, z), mat=frame)


# ------------------------------------------------------------------ outside

def school_front(film, o=(0, 0)):
    brick = material("brick", "#b5553c", 0.85)
    trim = material("trim", "#efe8da", 0.5)
    shapes.box(film, "Plaza", (26, 14, 0.04), _at(o, 0, 0.5, 0.02), mat=material("concrete", "#c9c4b8", 0.9))
    shapes.box(film, "Walkway", (3.2, 8, 0.05), _at(o, 0, -10, 0.02), mat=material("concrete", "#c9c4b8", 0.9))
    shapes.box(film, "School", (24, 7, 7.5), _at(o, 0, 11, 3.75), mat=brick)
    shapes.box(film, "Roofline", (24.4, 7.4, 0.45), _at(o, 0, 11, 7.6), mat=trim)
    shapes.box(film, "Base", (24.1, 7.1, 0.5), _at(o, 0, 11, 0.25), mat=material("stone", "#8d8579", 0.9))
    for z in (2.2, 5.3):
        for x in (-10, -7.5, -5, 5, 7.5, 10):
            _window(film, o, x, 7.46, z)
    # entrance
    shapes.box(film, "DoorFrame", (3.2, 0.2, 3.0), _at(o, 0, 7.45, 1.5), mat=trim)
    door = material("door_blue", "#2a4d8f", 0.4, coat=0.4)
    for x in (-0.68, 0.68):
        shapes.box(film, "Door", (1.25, 0.12, 2.5), _at(o, x, 7.36, 1.3), mat=door)
        shapes.box(film, "DoorWin", (0.6, 0.13, 0.9), _at(o, x, 7.35, 1.8), mat=material("window_glass", "#bfe0ff", 0.05, glow=0.6))
    shapes.box(film, "Canopy", (4.6, 1.8, 0.22), _at(o, 0, 6.6, 3.15), mat=trim)
    for x in (-2.1, 2.1):
        shapes.cylinder(film, "Column", 0.12, 3.1, _at(o, x, 5.85, 1.55), mat=trim)
    for i, (w, d) in enumerate(((5.0, 2.2), (4.4, 1.5), (3.8, 0.8))):
        shapes.box(film, "Step", (w, d, 0.15), _at(o, 0, 7.4 - d / 2, 0.075 + i * 0.15), mat=material("concrete", "#c9c4b8", 0.9))
    shapes.text(film, "Sign", "MAPLEWOOD ELEMENTARY", 0.62, _at(o, 0, 7.42, 4.35), mat=material("sign_text", "#f7f1e3", 0.4),
                depth=0.06)
    # flag
    shapes.cylinder(film, "Flagpole", 0.06, 9, _at(o, -7.5, 4.5, 4.5), mat=material("pole", "#d0d0d0", 0.3, metallic=0.8))
    shapes.box(film, "Flag", (1.5, 0.03, 0.9), _at(o, -6.7, 4.5, 8.4), mat=material("flag", "#2f5fb3", 0.7, sheen=0.4))
    # greenery
    for x in (-13, 13):
        props.tree(film, o[0] + x, o[1] + 5.5, height=3.4)
    for x in (-9, -5.5, 5.5, 9):
        props.bush(film, o[0] + x, o[1] + 7.0, size=0.6)
    props.bench(film, o[0] + 6, o[1] + 2.5, rotation=0)
    return {"door": _at(o, 0, 6.4), "stairs": _at(o, 0, 5.2), "left": _at(o, -12, -2), "plaza": _at(o, 0, 0)}


# ------------------------------------------------------------------ hallway

def hallway(film, o=(100, 0)):
    """A school hallway with a wall of lockers along the back. Ned's locker is at x = 0."""
    shapes.box(film, "HallFloor", (16, 8, 0.04), _at(o, 0, -1.5, 0.02), mat=material("hall_tile", "#ddd6c6", 0.35, coat=0.3))
    stripe = material("hall_stripe", "#8f2f2f", 0.4)
    shapes.box(film, "Stripe", (16, 0.18, 0.045), _at(o, 0, 0.6, 0.022), mat=stripe)
    shapes.box(film, "HallWall", (16, 0.25, 3.6), _at(o, 0, 1.95, 1.8), mat=material("hall_wall", "#efe6d2", 0.8))
    shapes.box(film, "HallCeiling", (16, 9, 0.2), _at(o, 0, -2.5, 3.6), mat=material("ceiling", "#f4f1ea", 0.9))
    shapes.box(film, "SideWallL", (0.25, 9, 3.6), _at(o, -8, -2.5, 1.8), mat=material("hall_wall", "#efe6d2", 0.8))
    shapes.box(film, "SideWallR", (0.25, 9, 3.6), _at(o, 8, -2.5, 1.8), mat=material("hall_wall", "#efe6d2", 0.8))
    for x in (-4.5, 0, 4.5):
        shapes.box(film, "CeilingLight", (2.4, 0.5, 0.04), _at(o, x, -0.6, 3.48), mat=material("ceiling_light", "#fffaf0", 0.5, glow=5))
        _area_light(film, "HallLight", _at(o, x, -1.0, 3.4), size=(3, 2.5), energy=260)
    _area_light(film, "HallFill", _at(o, 0, -6.5, 2.2), size=(10, 2), energy=500).rotation_euler = (math.radians(90), 0, 0)

    locker = material("locker", "#2f6db5", 0.45, metallic=0.3, coat=0.2)
    vent = material("locker_vent", "#1b3e6b", 0.6)
    handle = material("locker_handle", "#c7ccd3", 0.25, metallic=1.0)
    width = 0.44
    for i in range(-14, 15):
        x = i * width
        if i == 0:
            continue
        shapes.box(film, "Locker", (width - 0.02, 0.4, 1.8), _at(o, x, 1.62, 0.98), mat=locker, bevel=0.01)
        for k in range(3):
            shapes.box(film, "Vent", (0.26, 0.41, 0.025), _at(o, x, 1.62, 1.68 + k * 0.06), mat=vent)
        shapes.box(film, "Handle", (0.04, 0.42, 0.14), _at(o, x + 0.13, 1.62, 1.0), mat=handle)
    shapes.box(film, "LockerBase", (13, 0.42, 0.08), _at(o, 0, 1.62, 0.04), mat=vent)
    shapes.box(film, "LockerTop", (13, 0.44, 0.06), _at(o, 0, 1.62, 1.91), mat=vent)

    # Ned's locker: a dark, glowing stash behind a door that swings open
    shapes.box(film, "NedLockerBack", (width - 0.02, 0.06, 1.8), _at(o, 0, 1.8, 0.98), mat=material("locker_inside", "#191b22", 0.7))
    for sx in (-1, 1):
        shapes.box(film, "NedLockerSide", (0.02, 0.4, 1.8), _at(o, sx * (width / 2 - 0.02), 1.62, 0.98), mat=locker)
    shapes.box(film, "NedLockerGlow", (0.34, 0.02, 0.03), _at(o, 0, 1.55, 1.84), mat=material("stash_glow", "#ffd27a", 0.5, glow=12))
    glow = bpy.data.lights.new("StashGlow", "POINT")
    glow.energy = 6
    glow.color = (1.0, 0.8, 0.45)
    glow.shadow_soft_size = 0.2
    glow_obj = bpy.data.objects.new("StashGlow", glow)
    film.collection.objects.link(glow_obj)
    glow_obj.location = _at(o, 0, 1.45, 1.4)
    flavors = ["cherry", "watermelon", "blue raspberry", "grape", "green apple"]
    for s, z in enumerate((0.55, 1.0, 1.45)):
        shapes.box(film, "Shelf", (width - 0.05, 0.36, 0.02), _at(o, 0, 1.62, z - 0.02), mat=material("shelf", "#3a3d46", 0.6))
        for k in range(10):
            col = props.CANDY_FLAVORS[flavors[(k + s) % len(flavors)]]
            row, colm = divmod(k, 5)
            shapes.box(film, "StashCandy", (0.05, 0.026, 0.014),
                       _at(o, -0.14 + colm * 0.07, 1.52 + row * 0.12, z + 0.01 + row * 0.012),
                       (0, 0, (k * 0.7) % 0.5 - 0.25), mat=material(f"candy_{col}", col, 0.08, coat=1.0, transmission=0.35))
    hinge = shapes.empty(film, "NedLockerHinge", _at(o, -width / 2 + 0.01, 1.42, 0.98))
    shapes.box(film, "NedLockerDoor", (width - 0.03, 0.025, 1.78), (width / 2 - 0.01, 0, 0), mat=locker, parent=hinge, bevel=0.005)
    for k in range(3):
        shapes.box(film, "Vent", (0.26, 0.03, 0.025), (width / 2, -0.005, 0.7 + k * 0.06), mat=vent, parent=hinge)
    shapes.box(film, "Handle", (0.04, 0.04, 0.14), (width - 0.08, -0.02, 0.02), mat=handle, parent=hinge)
    shapes.text(film, "LockerNum", "4B", 0.09, (width / 2, -0.02, 0.55), mat=material("sign_text", "#f7f1e3", 0.4),
                parent=hinge, depth=0.004)

    # decorations
    shapes.text(film, "Banner", "GO MAPLEWOOD BEAVERS!", 0.28, _at(o, 0, 1.8, 2.75), mat=material("banner_text", "#8f2f2f", 0.5), depth=0.02)
    for x, col in ((-5.2, "#ffcc4d"), (-3.4, "#7ecbff"), (3.6, "#a5e07a"), (5.3, "#ff9db0")):
        shapes.box(film, "Poster", (0.7, 0.02, 0.5), _at(o, x, 1.81, 2.35), mat=material(f"poster_{col}", col, 0.7))
    shapes.cylinder(film, "TrashCan", 0.22, 0.6, _at(o, 6.6, 1.2, 0.3), mat=material("trash", "#5d6670", 0.5))
    return {"locker": _at(o, 0, 0.75), "door_hinge": hinge, "line": [_at(o, 1.2 + i * 0.75, 0.55) for i in range(5)],
            "left": _at(o, -6, -0.3)}


# ---------------------------------------------------------------- classroom

def kid_desk(film, x, y, face_angle=0):
    """A student desk with its chair behind it. Kids sitting here face +y (toward the board)."""
    wood = material("desk_wood", "#d1a46b", 0.55, coat=0.2)
    metal = material("desk_metal", "#59606a", 0.4, metallic=0.6)
    shapes.box(film, "DeskTop", (0.66, 0.46, 0.035), (x, y, 0.6), mat=wood, bevel=0.008)
    for dx in (-0.29, 0.29):
        for dy in (-0.19, 0.19):
            shapes.cylinder(film, "DeskLeg", 0.015, 0.6, (x + dx, y + dy, 0.3), mat=metal, segments=8)
    cy = y - 0.5
    shapes.box(film, "Seat", (0.4, 0.38, 0.03), (x, cy, 0.33), mat=material("chair_blue", "#3f6fb3", 0.5, coat=0.3), bevel=0.01)
    shapes.box(film, "ChairBack", (0.4, 0.03, 0.3), (x, cy - 0.19, 0.55), mat=material("chair_blue", "#3f6fb3", 0.5, coat=0.3), bevel=0.01)
    for dx in (-0.17, 0.17):
        for dy in (-0.16, 0.16):
            shapes.cylinder(film, "ChairLeg", 0.012, 0.33, (x + dx, cy + dy, 0.165), mat=metal, segments=8)
    return (x, cy)


def classroom(film, o=(200, 0)):
    shapes.box(film, "ClassFloor", (11, 10, 0.04), _at(o, 0, 0, 0.02), mat=material("class_floor", "#b9895a", 0.5, coat=0.2))
    wall = material("class_wall", "#e7efe0", 0.85)
    shapes.box(film, "BackWall", (11, 0.25, 3.6), _at(o, 0, 4.4, 1.8), mat=wall)
    shapes.box(film, "LeftWall", (0.25, 10, 3.6), _at(o, -5.5, 0, 1.8), mat=wall)
    shapes.box(film, "RightWall", (0.25, 10, 3.6), _at(o, 5.5, 0, 1.8), mat=wall)
    shapes.box(film, "FrontWall", (11, 0.25, 3.6), _at(o, 0, -5.0, 1.8), mat=wall)
    shapes.box(film, "ClassCeiling", (11, 10, 0.2), _at(o, 0, 0, 3.6), mat=material("ceiling", "#f4f1ea", 0.9))
    for x, y in ((-2.5, 1.5), (2.5, 1.5), (-2.5, -2.5), (2.5, -2.5)):
        shapes.box(film, "CeilingLight", (1.8, 0.6, 0.04), _at(o, x, y, 3.48), mat=material("ceiling_light", "#fffaf0", 0.5, glow=5))
        _area_light(film, "ClassLight", _at(o, x, y, 3.4), size=(2.2, 1.2), energy=170)
    # chalkboard
    shapes.box(film, "BoardFrame", (4.9, 0.08, 1.75), _at(o, 0, 4.25, 1.75), mat=material("board_frame", "#8a5a33", 0.6))
    shapes.box(film, "Board", (4.6, 0.1, 1.5), _at(o, 0, 4.22, 1.75), mat=material("chalkboard", "#2e4a3b", 0.85))
    chalk = material("chalk", "#f0f0e8", 0.9, glow=0.3)
    shapes.text(film, "BoardText", "NO CANDY IN CLASS!", 0.3, _at(o, 0, 4.16, 2.1), mat=chalk, depth=0.003)
    shapes.text(film, "BoardMath", "2 + 2 = 4", 0.22, _at(o, -1.0, 4.16, 1.5), mat=chalk, depth=0.003)
    shapes.text(film, "BoardDate", "Tuesday", 0.18, _at(o, 1.4, 4.16, 1.45), mat=chalk, depth=0.003)
    # clock
    clock = shapes.cylinder(film, "Clock", 0.25, 0.05, _at(o, 3.4, 4.25, 2.8), (math.pi / 2, 0, 0), mat=material("clock", "#fafafa", 0.4))
    shapes.box(film, "ClockHand", (0.02, 0.02, 0.16), (0, 0.03, 0.06), (0, 0.4, 0), mat=material("pupil", "#111111", 0.4), parent=clock)
    # windows on the left wall
    for y in (-2.5, 0, 2.5):
        _window(film, o, -5.36, y, 1.9, w=1.6, h=1.5, facing_y=False)
    # posters
    for y, col in ((-1.5, "#ffcf5c"), (1.6, "#8ed1fc")):
        shapes.box(film, "Poster", (0.02, 0.8, 0.6), _at(o, 5.36, y, 1.9), mat=material(f"poster_{col}", col, 0.7))
    # teacher desk with an apple
    shapes.box(film, "TeacherDesk", (1.5, 0.75, 0.76), _at(o, -3.0, 3.0, 0.38), mat=material("teacher_desk", "#8a5a33", 0.5, coat=0.3), bevel=0.02)
    apple = shapes.sphere(film, "Apple", 0.06, _at(o, -2.6, 3.0, 0.82), mat=material("apple", "#c62828", 0.3, coat=0.6))
    shapes.cylinder(film, "Stem", 0.006, 0.03, (0, 0, 0.065), mat=material("trunk", "#7a5230", 0.8), parent=apple)
    seats = {}
    for row, y in enumerate((1.4, -0.3, -2.0)):
        for colm, x in enumerate((-2.2, 0.0, 2.2)):
            seats[(row, colm)] = kid_desk(film, o[0] + x, o[1] + y)
    return {"front": _at(o, 0, 3.2), "teacher_desk": _at(o, -3.0, 2.3), "seats": seats, "door": _at(o, 4.6, -3.8)}


# --------------------------------------------------------------- playground

def playground(film, o=(300, 0)):
    shapes.box(film, "WoodChips", (12, 9, 0.05), _at(o, 0, 4, 0.025), mat=material("woodchips", "#9c7550", 0.95))
    shapes.box(film, "Blacktop", (14, 6, 0.04), _at(o, 0, -2.5, 0.02), mat=material("blacktop", "#55585d", 0.8))
    for i in range(4):
        shapes.box(film, "Hopscotch", (0.5, 0.5, 0.045), _at(o, -5 + i * 0.55, -3.5, 0.022), mat=material("chalk_yellow", "#f2d54b", 0.9))
    # slide
    red, yellow = material("slide_red", "#d93a32", 0.4, coat=0.4), material("slide_yellow", "#f2c230", 0.4, coat=0.4)
    for dx in (-0.45, 0.45):
        for dy in (-0.45, 0.45):
            shapes.cylinder(film, "SlidePost", 0.05, 2.4, _at(o, -4 + dx, 6 + dy, 1.2), mat=red)
    shapes.box(film, "SlideDeck", (1.0, 1.0, 0.08), _at(o, -4, 6, 1.5), mat=yellow)
    shapes.box(film, "SlideRoof", (1.2, 1.2, 0.1), _at(o, -4, 6, 2.45), mat=red)
    shapes.box(film, "SlideChute", (0.6, 2.6, 0.06), _at(o, -4, 4.3, 0.85), (math.radians(-33), 0, 0), mat=yellow)
    # swings
    metal = material("swing_metal", "#4a6fa5", 0.35, metallic=0.6)
    for x in (2.5, 5.5):
        for dy in (-0.6, 0.6):
            shapes.cylinder(film, "SwingLeg", 0.05, 2.6, _at(o, x, 6.5 + dy, 1.3), mat=metal)
    shapes.cylinder(film, "SwingBar", 0.05, 3.2, _at(o, 4, 6.5, 2.55), (0, math.pi / 2, 0), mat=metal)
    for x in (3.3, 4.7):
        for dx in (-0.2, 0.2):
            shapes.cylinder(film, "Chain", 0.008, 1.9, _at(o, x + dx, 6.5, 1.6), mat=material("lamp_metal", "#9a9a9a", 0.3, metallic=1.0), segments=6)
        shapes.box(film, "SwingSeat", (0.5, 0.2, 0.04), _at(o, x, 6.5, 0.65), mat=material("seat_black", "#1e1e1e", 0.6))
    props.fence(film, (o[0] - 14, o[1] + 10), (o[0] + 14, o[1] + 10))
    for x in (-10, 10):
        props.tree(film, o[0] + x, o[1] + 8, height=3.3)
    props.bench(film, o[0] - 7, o[1] + 1.5, rotation=0)
    # Ned's office: a milk crate, a cardboard sign and the money
    office = _at(o, 0, 2.2)
    props.crate(film, office[0], office[1])
    cardboard = material("cardboard", "#b88a55", 0.85)
    shapes.cylinder(film, "SignStick", 0.015, 1.1, _at(o, -0.55, 2.45, 0.55), mat=material("trunk", "#7a5230", 0.8), segments=8)
    shapes.box(film, "SignBoard", (0.7, 0.03, 0.4), _at(o, -0.55, 2.43, 1.15), mat=cardboard)
    shapes.text(film, "SignText", "NED'S\nCANDY", 0.12, _at(o, -0.55, 2.41, 1.15), mat=material("marker", "#1a1a1a", 0.7), depth=0.003)
    pile = props.cash_pile(film, office[0] + 0.5, office[1] + 0.1, bundles=6)
    pile.scale = (0.6, 0.6, 0.6)
    return {"office": office, "pile": pile, "line": [_at(o, 1.6 + i * 0.8, 1.3) for i in range(6)], "left": _at(o, -9, -1)}
