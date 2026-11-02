"""Set pieces: ground, paths, trees, houses, benches, lamps, fences, flowers, balls...

Every function takes the film first, then a position in meters (x, y) on the ground.
They return the object(s) they make, so you can animate them later.
"""

import math

from mathutils import Vector

from . import shapes
from .materials import material


def ground(film, size=80, color="#5fa84a"):
    return shapes.box(film, "Ground", (size, size, 0.2), (0, 0, -0.1), mat=material("grass", color, 0.9))


def path(film, start, end, width=2.0, color="#d9c79a"):
    a, b = Vector((*start, 0)), Vector((*end, 0))
    mid, d = (a + b) / 2, b - a
    angle = math.atan2(d.y, d.x)
    return shapes.box(film, "Path", (d.length, width, 0.04), (mid.x, mid.y, 0.02), (0, 0, angle),
                      mat=material("path", color, 0.95))


def tree(film, x, y, height=3.2, leaves="#4f9e3a", trunk="#7a5230"):
    """Returns the leafy top (an empty) so you can wiggle it: film.wiggle(top)."""
    shapes.cylinder(film, "Trunk", 0.33, height, (x, y, height / 2), mat=material("trunk", trunk, 0.8),
                    top_radius=0.24)
    top = shapes.empty(film, "TreeTop", (x, y, height + 1.2))
    m = material(f"leaves_{leaves}", leaves, 0.8)
    shapes.sphere(film, "Leaves", 2.0, (0, 0, 0.2), mat=m, parent=top)
    shapes.sphere(film, "Leaves", 1.4, (1.3, 0.5, -0.5), mat=m, parent=top)
    shapes.sphere(film, "Leaves", 1.3, (-1.2, 0.6, -0.4), mat=m, parent=top)
    shapes.sphere(film, "Leaves", 1.2, (0.2, 0.9, 1.2), mat=m, parent=top)
    return top


def bush(film, x, y, size=0.8, color="#3f8f34"):
    m = material(f"bush_{color}", color, 0.85)
    shapes.sphere(film, "Bush", size, (x, y, size * 0.6), mat=m)
    shapes.sphere(film, "Bush", size * 0.75, (x + size * 0.8, y + 0.1, size * 0.45), mat=m)


def house(film, x, y, walls="#f0dcc0", roof="#b94a3c", rotation=0):
    rot = (0, 0, math.radians(rotation))
    base = shapes.empty(film, "House", (x, y, 0))
    base.rotation_euler = rot
    shapes.box(film, "Walls", (6, 5, 4), (0, 0, 2), mat=material(f"walls_{walls}", walls, 0.85), parent=base,
               bevel=0.05)
    # A triangular prism lying along X with its point up, squashed to a gentle slope.
    m_roof = material(f"roof_{roof}", roof, 0.6)
    roof_obj = shapes.cylinder(film, "Roof", 3.9, 6.6, (0, 0, 4.0 + 0.975), (0, -math.pi / 2, 0), mat=m_roof,
                               parent=base, segments=3)
    roof_obj.scale = (0.5, 1, 1)
    for poly in roof_obj.data.polygons:
        poly.use_smooth = False
    shapes.box(film, "Door", (1.2, 0.1, 2.2), (0, -2.52, 1.1), mat=material("door", "#7a4a2a", 0.6), parent=base)
    glass = material("window", "#a8d8ff", 0.1)
    for wx in (-1.9, 1.9):
        shapes.box(film, "Window", (1.1, 0.1, 1.1), (wx, -2.52, 2.4), mat=glass, parent=base)
    return base


def bench(film, x, y, rotation=0):
    base = shapes.empty(film, "Bench", (x, y, 0))
    base.rotation_euler = (0, 0, math.radians(rotation))
    wood = material("bench_wood", "#9c6b3f", 0.7)
    metal = material("metal", "#3a3a3a", 0.4, metallic=0.6)
    shapes.box(film, "Seat", (2.0, 0.6, 0.08), (0, 0, 0.48), mat=wood, parent=base, bevel=0.02)
    shapes.box(film, "Back", (2.0, 0.08, 0.45), (0, 0.3, 0.8), mat=wood, parent=base, bevel=0.02)
    for lx in (-0.85, 0.85):
        shapes.box(film, "Leg", (0.08, 0.55, 0.46), (lx, 0, 0.23), mat=metal, parent=base)
    return base


def lamp(film, x, y, height=3.2):
    metal = material("lamp_metal", "#2e2e2e", 0.4, metallic=0.5)
    shapes.cylinder(film, "LampPost", 0.07, height, (x, y, height / 2), mat=metal)
    return shapes.sphere(film, "LampBulb", 0.22, (x, y, height + 0.15), mat=material("bulb", "#fff1c4", 0.3, glow=4))


def fence(film, start, end, color="#f4f4f4"):
    a, b = Vector((*start, 0)), Vector((*end, 0))
    d = b - a
    angle = math.atan2(d.y, d.x)
    m = material(f"fence_{color}", color, 0.7)
    for z in (0.35, 0.75):
        mid = (a + b) / 2
        shapes.box(film, "Rail", (d.length, 0.06, 0.1), (mid.x, mid.y, z), (0, 0, angle), mat=m)
    posts = max(1, int(d.length / 1.5))
    for i in range(posts + 1):
        p = a.lerp(b, i / posts)
        shapes.box(film, "Post", (0.12, 0.12, 1.0), (p.x, p.y, 0.5), mat=m, bevel=0.02)


def flowers(film, x, y, count=20, radius=1.5):
    colors = ["#ff5a7a", "#ffd23c", "#b47cff", "#ffffff", "#ff8c3c"]
    stem = material("stem", "#3c8c32", 0.8)
    for i in range(count):
        angle = i * 2.39996
        r = radius * math.sqrt((i + 0.5) / count)
        px, py = x + math.cos(angle) * r, y + math.sin(angle) * r
        shapes.cylinder(film, "Stem", 0.015, 0.3, (px, py, 0.15), mat=stem, segments=6)
        c = colors[i % len(colors)]
        shapes.sphere(film, "Flower", 0.07, (px, py, 0.32), mat=material(f"flower_{c}", c, 0.5),
                      segments=12, rings=8)


def ball(film, x, y, z=None, radius=0.22, color="#e23b3b"):
    z = radius if z is None else z
    return shapes.sphere(film, "Ball", radius, (x, y, z), mat=material(f"ball_{color}", color, 0.3))


def rock(film, x, y, size=0.5, color="#8a8a8a"):
    obj = shapes.sphere(film, "Rock", size, (x, y, size * 0.35), (1.2, 1.0, 0.6),
                        mat=material(f"rock_{color}", color, 0.9), segments=10, rings=6)
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj
