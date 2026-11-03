"""Low-level helpers that create mesh objects without needing the Blender UI."""

import math

import bmesh
import bpy
from mathutils import Vector


def _link(film, obj, parent):
    film.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent


def empty(film, name, location=(0, 0, 0), parent=None):
    """An invisible pivot. Characters use these as joints."""
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = 0.1
    _link(film, obj, parent)
    obj.location = location
    return obj


def _object(film, name, bm, location, scale, rotation, mat, parent, smooth):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    if mat is not None:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    _link(film, obj, parent)
    obj.location = location
    obj.scale = scale
    obj.rotation_euler = rotation
    return obj


def sphere(film, name, radius=1.0, location=(0, 0, 0), scale=(1, 1, 1), mat=None,
           parent=None, cut_below=None, segments=32, rings=16, keep=None, rotation=(0, 0, 0)):
    """A smooth ball. scale stretches it into an egg/capsule shape.
    cut_below (-1..1) removes the bottom part, e.g. 0.3 keeps only a cap (hair).
    keep(x, y, z) -> bool (coordinates of a unit sphere) keeps only matching vertices."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    if cut_below is not None:
        doomed = [v for v in bm.verts if v.co.z < cut_below * radius]
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    if keep is not None:
        doomed = [v for v in bm.verts if not keep(v.co.x / radius, v.co.y / radius, v.co.z / radius)]
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    return _object(film, name, bm, location, scale, rotation, mat, parent, True)


def box(film, name, size=(1, 1, 1), location=(0, 0, 0), rotation=(0, 0, 0), mat=None,
        parent=None, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    obj = _object(film, name, bm, location, (1, 1, 1), rotation, mat, parent, False)
    if bevel > 0:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def cylinder(film, name, radius=0.5, depth=1.0, location=(0, 0, 0), rotation=(0, 0, 0),
             mat=None, parent=None, top_radius=None, segments=24):
    """A cylinder standing on its base (location is the center). top_radius makes a cone."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius if top_radius is None else top_radius,
                          depth=depth)
    obj = _object(film, name, bm, location, (1, 1, 1), rotation, mat, parent, True)
    # keep the flat caps crisp
    for poly in obj.data.polygons:
        if abs(poly.normal.z) > 0.9:
            poly.use_smooth = False
    return obj


def capsule(film, name, r_top, r_bottom, length, location=(0, 0, 0), mat=None, parent=None,
            scale=(1, 1, 1), segments=24, rings=12):
    """A rounded, tapered limb hanging down from `location`: a ball of r_top at the top,
    a ball of r_bottom `length` lower, smoothly joined."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        if z >= -1e-6:
            v.co = Vector((x * r_top, y * r_top, z * r_top))
        else:
            v.co = Vector((x * r_bottom, y * r_bottom, -length + z * r_bottom))
    return _object(film, name, bm, location, scale, (0, 0, 0), mat, parent, True)


def tube(film, name, points, radius=0.01, location=(0, 0, 0), mat=None, parent=None,
         closed=False, segments=8, rotation=(0, 0, 0)):
    """A smooth tube through a list of points (lips, eyebrows, chains, strings, frames).
    radius can be a number or a list (one per point) to taper it."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    radii = radius if isinstance(radius, (list, tuple)) else [radius] * n
    bm = bmesh.new()
    rings = []
    prev_normal = None
    for i, p in enumerate(pts):
        if closed:
            a, b = pts[(i - 1) % n], pts[(i + 1) % n]
        else:
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        tangent = (b - a).normalized()
        if prev_normal is None:
            ref = Vector((0, 0, 1)) if abs(tangent.z) < 0.9 else Vector((1, 0, 0))
            normal = tangent.cross(ref).normalized()
        else:
            normal = (prev_normal - tangent * prev_normal.dot(tangent)).normalized()
        prev_normal = normal
        binormal = tangent.cross(normal)
        ring = []
        for j in range(segments):
            ang = 2 * math.pi * j / segments
            ring.append(bm.verts.new(p + (normal * math.cos(ang) + binormal * math.sin(ang)) * radii[i]))
        rings.append(ring)
    count = n if closed else n - 1
    for i in range(count):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for j in range(segments):
            bm.faces.new((r0[j], r0[(j + 1) % segments], r1[(j + 1) % segments], r1[j]))
    if not closed:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _object(film, name, bm, location, (1, 1, 1), rotation, mat, parent, True)


def text(film, name, body, size=0.3, location=(0, 0, 0), rotation=(math.pi / 2, 0, 0), mat=None,
         parent=None, depth=0.01, align="CENTER"):
    """3D text (signs, chalkboards). By default it stands upright facing the -Y direction."""
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.size = size
    curve.extrude = depth
    curve.align_x = align
    curve.align_y = "CENTER"
    obj = bpy.data.objects.new(name, curve)
    _link(film, obj, parent)
    obj.location = location
    obj.rotation_euler = rotation
    if mat is not None:
        curve.materials.append(mat)
    return obj
