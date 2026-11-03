"""Colors and simple toy-like materials."""

import bpy


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def color(value):
    """Turns "#ff8800", (255, 136, 0) or (1.0, 0.5, 0.0) into a linear RGB tuple."""
    if isinstance(value, str):
        h = value.lstrip("#")
        rgb = tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    elif any(v > 1 for v in value):
        rgb = tuple(v / 255 for v in value)
    else:
        rgb = tuple(value)
    return tuple(_srgb_to_linear(c) for c in rgb[:3])


def _bsdf(mat):
    if mat.node_tree is None:
        mat.use_nodes = True
    for node in mat.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    return mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")


def _set(bsdf, name, value):
    if name in bsdf.inputs:
        bsdf.inputs[name].default_value = value


def material(name, base, roughness=0.55, metallic=0.0, glow=0.0, sheen=0.0, coat=0.0,
             transmission=0.0, subsurface=0.0):
    """A material. glow lights it up (bulbs, screens), sheen = soft cloth, coat = glossy
    varnish, transmission = see-through (candy, glass), subsurface = soft skin."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    rgb = color(base)
    mat = bpy.data.materials.new(name)
    bsdf = _bsdf(mat)
    _set(bsdf, "Base Color", (*rgb, 1.0))
    _set(bsdf, "Roughness", roughness)
    _set(bsdf, "Metallic", metallic)
    if glow > 0:
        _set(bsdf, "Emission Color", (*rgb, 1.0))
        _set(bsdf, "Emission Strength", glow)
    if sheen > 0:
        _set(bsdf, "Sheen Weight", sheen)
    if coat > 0:
        _set(bsdf, "Coat Weight", coat)
    if transmission > 0:
        _set(bsdf, "Transmission Weight", transmission)
    if subsurface > 0:
        _set(bsdf, "Subsurface Weight", subsurface)
        _set(bsdf, "Subsurface Radius", (0.9, 0.35, 0.2))
        _set(bsdf, "Subsurface Scale", 0.01)
    mat.diffuse_color = (*rgb, 1.0)  # color in the viewport
    return mat
