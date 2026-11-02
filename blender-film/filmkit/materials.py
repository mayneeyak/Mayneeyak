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


def material(name, base, roughness=0.55, metallic=0.0, glow=0.0):
    """A plastic-looking material. glow > 0 makes it light up (bulbs, screens)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    rgb = color(base)
    mat = bpy.data.materials.new(name)
    bsdf = _bsdf(mat)
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if glow > 0:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Emission Strength"].default_value = glow
    mat.diffuse_color = (*rgb, 1.0)  # color in the viewport
    return mat
