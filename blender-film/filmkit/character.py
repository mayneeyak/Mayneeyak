"""Refined cartoon characters: a real joint rig, planted feet (leg IK), natural walk cycles,
overlapping motion, breathing, blinking, and a face that can smile, smirk and talk."""

import math
import random

from mathutils import Euler, Matrix, Vector

from . import shapes
from .materials import material
from .moves import MOVES

# Body proportions (meters, before `scale`). Kids have bigger heads and shorter limbs.
BUILDS = {
    "kid": dict(hip_w=0.08, hip_drop=0.035, thigh=0.24, shin=0.23, ankle=0.055, spine=0.33, neck=0.045,
                head=0.165, shoulder_w=0.165, shoulder_z=0.27, upper=0.17, fore=0.16, hand=0.052,
                torso=(0.158, 0.152), arm_r=0.05, leg_r=0.068, foot=(0.056, 0.105, 0.04), sole=0.018),
    "adult": dict(hip_w=0.1, hip_drop=0.05, thigh=0.42, shin=0.4, ankle=0.065, spine=0.5, neck=0.07,
                  head=0.135, shoulder_w=0.215, shoulder_z=0.43, upper=0.28, fore=0.25, hand=0.066,
                  torso=(0.205, 0.188), arm_r=0.062, leg_r=0.088, foot=(0.064, 0.135, 0.045), sole=0.022),
}

# How a walk looks. step/speed/lift/bob are relative to leg length.
WALK_STYLES = {
    "normal": dict(step=0.8, speed=1.6, lift=0.1, bob=0.035, sway=0.02, twist=7, counter=1.3, arm=22,
                   elbow=18, out=6, lean=3, head_bob=0, crouch=0.0),
    "swagger": dict(step=0.75, speed=1.15, lift=0.12, bob=0.075, sway=0.04, twist=9, counter=2.3, arm=24,
                    elbow=28, out=16, lean=-6, head_bob=7, crouch=0.0),
    "run": dict(step=1.55, speed=3.6, lift=0.32, bob=0.06, sway=0.015, twist=10, counter=1.4, arm=48,
                elbow=88, out=8, lean=14, head_bob=0, crouch=0.03),
    "sneak": dict(step=0.5, speed=0.75, lift=0.16, bob=0.02, sway=0.015, twist=4, counter=1.0, arm=10,
                  elbow=75, out=10, lean=16, head_bob=0, crouch=0.09),
}

# Overlapping action: parts further from the hips follow a little later.
DELAY = {"pelvis": 0.0, "leg": 0.0, "spine": 0.03, "shoulder": 0.05, "neck": 0.07, "elbow": 0.09,
         "wrist": 0.11, "face": 0.0, "glasses": 0.05}

DEFAULT_FACE = dict(lids=0.85, smile=0.35, smirk=0.0, look=(0, 0), glasses=0.0, brow_raise=0.0, brow_angle=0.0)


def _rad(deg):
    return math.radians(deg)


def _unwrap(current, target):
    """The target angle closest to current (so turns never spin the long way)."""
    return current + (target - current + math.pi) % (2 * math.pi) - math.pi


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _point(target):
    """Accepts a Character, (x, y) or (x, y, z) and returns a 3D Vector."""
    if isinstance(target, Character):
        return target.head_position()
    if hasattr(target, "matrix_world"):
        return target.matrix_world.translation.copy()
    if len(target) == 2:
        return Vector((target[0], target[1], 0.0))
    return Vector(target)


class Character:
    """A cartoon character with a full rig.

    build: "kid" or "adult".  Colors are "#rrggbb" strings.
    top: "tshirt", "hoodie", "cardigan" or "suit".   bottom: "pants", "shorts" or "skirt".
    hair_style: "short", "buzz", "long", "ponytail", "bun" or "bald".
    Accessories: cap="#color" (cap_backwards=True), sunglasses=True, glasses="#color", chain=True,
                 tie="#color", mustache=True, backpack="#color".
    face: default expression, e.g. {"lids": 0.6, "smirk": 0.5} for a cool, half-lidded look.
    """

    def __init__(self, film, name, build="kid", skin="#f1c7a3", shirt="#3d8bff", pants="#2c3e66",
                 shoes="#333333", sole="#f2f2f2", hair="#4a2f1b", hair_style=None, long_hair=False,
                 top="tshirt", bottom="pants", inner="#f4f4f4", eye_color="#5b3a1a", cap=None,
                 cap_backwards=False, sunglasses=False, glasses=None, chain=False, tie=None,
                 mustache=False, backpack=None, face=None, scale=1.0, width=1.0):
        self.film = film
        self.name = name
        self.scale = scale
        d = dict(BUILDS[build])
        for key in ("hip_w", "shoulder_w", "arm_r", "leg_r"):
            d[key] *= 1 + (width - 1) * 0.6
        d["torso"] = tuple(r * width for r in d["torso"])
        self.d = d
        self.build = build
        self.leg_len = d["thigh"] + d["shin"]
        self.P = d["hip_drop"] + d["ankle"] + 0.985 * self.leg_len  # pelvis height
        hr = d["head"]
        self.hr = hr
        self.head_center = self.P + 0.02 + d["spine"] + d["neck"] + hr * 0.92
        self.x, self.y, self.angle = 0.0, 0.0, 0.0
        self.current_pose = {}
        self.seated = None
        self.face_state = dict(DEFAULT_FACE, **(face or {}))
        self.springs = []
        self.talking = []
        hair_style = hair_style or ("long" if long_hair else "short")
        film.characters.append(self)

        n = name
        mats = {
            "skin": material(f"{n}_skin", skin, 0.5, subsurface=0.08),
            "shirt": material(f"{n}_shirt", shirt, 0.8, sheen=0.4),
            "pants": material(f"{n}_pants", pants, 0.85, sheen=0.3),
            "shoes": material(f"{n}_shoes", shoes, 0.45, coat=0.3),
            "sole": material(f"{n}_sole", sole, 0.6),
            "hair": material(f"{n}_hair", hair, 0.55, sheen=0.5),
            "inner": material(f"{n}_inner", inner, 0.8, sheen=0.3),
            "white": material("eye_white", "#fbfbfb", 0.2, coat=0.6),
            "iris": material(f"{n}_iris", eye_color, 0.3, coat=0.8),
            "pupil": material("eye_pupil", "#0d0a08", 0.2, coat=0.8),
            "shine": material("eye_shine", "#ffffff", 0.2, glow=6),
            "lips": material(f"{n}_lips", "#7a2e2a", 0.45),
            "mouth": material("mouth_inside", "#3a1212", 0.6),
        }
        self.mats = mats
        E = shapes.empty
        f = film

        # ---------------------------------------------------------------- rig
        self.root = E(f, n)
        self.root.scale = (scale, scale, scale)
        self.pelvis = E(f, f"{n}_pelvis", (0, 0, self.P), self.root)
        self.spine = E(f, f"{n}_spine", (0, 0, 0.02), self.pelvis)
        self.breath = E(f, f"{n}_breath", (0, 0, 0), self.spine)
        self.neck = E(f, f"{n}_neck", (0, 0, d["spine"]), self.spine)
        self.head = E(f, f"{n}_head", (0, 0, d["neck"]), self.neck)  # idle motion lives here

        # ------------------------------------------------------------- torso
        r0, r1 = d["torso"]
        top_z, bot_z = d["spine"] - r0 * 0.5, r1 * 0.55
        torso_mat = mats["shirt"]
        shapes.capsule(f, f"{n}_torso", r0, r1, top_z - bot_z, (0, 0, top_z), torso_mat, self.breath,
                       scale=(1, 0.74, 1))
        shapes.sphere(f, f"{n}_hipsmesh", 1, (0, 0, 0.0), (r1 * 1.02, r1 * 0.78, r1 * 0.72),
                      mats["pants"] if bottom != "skirt" else torso_mat, self.pelvis)
        shapes.capsule(f, f"{n}_neckmesh", hr * 0.3, hr * 0.33, d["neck"] + 0.04, (0, 0, d["neck"] + 0.01),
                       mats["skin"], self.neck)
        self._dress_top(top, mats, inner, r0, r1, top_z, bot_z, hr)
        if bottom == "skirt":
            depth = d["thigh"] * 0.85
            shapes.cylinder(f, f"{n}_skirt", r1 * 1.65, depth, (0, 0, -depth / 2 + 0.03), mat=mats["pants"],
                            parent=self.pelvis, top_radius=r1 * 1.02, segments=28)

        # -------------------------------------------------------------- legs
        thigh_mat = mats["skin"] if bottom == "skirt" else mats["pants"]
        shin_mat = mats["skin"] if bottom in ("skirt", "shorts") else mats["pants"]
        lr = d["leg_r"]
        self.hip, self.knee, self.ankle = {}, {}, {}
        self.shoulder, self.elbow, self.wrist, self.grip = {}, {}, {}, {}
        for side, sx in (("r", -1), ("l", 1)):
            hip = E(f, f"{n}_hip_{side}", (sx * d["hip_w"], 0, -d["hip_drop"]), self.pelvis)
            shapes.capsule(f, f"{n}_thigh_{side}", lr, lr * 0.84, d["thigh"], (0, 0, 0), thigh_mat, hip)
            knee = E(f, f"{n}_knee_{side}", (0, 0, -d["thigh"]), hip)
            shapes.capsule(f, f"{n}_shin_{side}", lr * 0.84, lr * 0.66, d["shin"], (0, 0, 0), shin_mat, knee)
            if bottom == "shorts":
                shapes.capsule(f, f"{n}_shortleg_{side}", lr * 1.12, lr * 1.0, d["thigh"] * 0.55, (0, 0, 0.0),
                               mats["pants"], hip)
            ankle = E(f, f"{n}_ankle_{side}", (0, 0, -d["shin"]), knee)
            fw, fl, fh = d["foot"]
            sh = d["sole"]
            shapes.sphere(f, f"{n}_shoe_{side}", 1, (0, -fl * 0.3, -d["ankle"] + sh + fh * 0.8),
                          (fw * 1.08, fl * 1.05, fh * 1.2), mats["shoes"], ankle)
            shapes.box(f, f"{n}_sole_{side}", (fw * 1.9, fl * 1.95, sh), (0, -fl * 0.3, -d["ankle"] + sh / 2),
                       mat=mats["sole"], parent=ankle, bevel=sh * 0.45)
            self.hip[side], self.knee[side], self.ankle[side] = hip, knee, ankle

            # arms
            ar = d["arm_r"]
            sleeve_long = top in ("hoodie", "cardigan", "suit")
            sh_ = E(f, f"{n}_shoulder_{side}", (sx * d["shoulder_w"], 0, d["shoulder_z"]), self.spine)
            shapes.capsule(f, f"{n}_upperarm_{side}", ar, ar * 0.88, d["upper"], (0, 0, 0),
                           torso_mat if sleeve_long else mats["skin"], sh_)
            if not sleeve_long:
                shapes.capsule(f, f"{n}_sleeve_{side}", ar * 1.18, ar * 1.08, d["upper"] * 0.42, (0, 0, 0.005),
                               torso_mat, sh_)
            el = E(f, f"{n}_elbow_{side}", (0, 0, -d["upper"]), sh_)
            shapes.capsule(f, f"{n}_forearm_{side}", ar * 0.88, ar * 0.72, d["fore"], (0, 0, 0),
                           torso_mat if sleeve_long else mats["skin"], el)
            wr = E(f, f"{n}_wrist_{side}", (0, 0, -d["fore"]), el)
            hs = d["hand"]
            shapes.sphere(f, f"{n}_hand_{side}", 1, (0, 0, -hs * 0.85), (hs * 0.62, hs * 0.95, hs * 1.15),
                          mats["skin"], wr)
            thumb = shapes.capsule(f, f"{n}_thumb_{side}", hs * 0.28, hs * 0.24, hs * 0.65,
                                   (-sx * hs * 0.35, -hs * 0.5, -hs * 0.45), mats["skin"], wr)
            thumb.rotation_euler = (-0.9, sx * 0.35, 0)
            self.grip[side] = E(f, f"{n}_grip_{side}", (-sx * hs * 0.45, -hs * 0.35, -hs * 1.1), wr)
            self.shoulder[side], self.elbow[side], self.wrist[side] = sh_, el, wr

        # -------------------------------------------------------------- head
        self._build_head(mats, hair_style, cap, cap_backwards, sunglasses, glasses, mustache)
        if chain:
            self._build_chain(r0, top_z)
        if tie:
            self._build_tie(tie, r0, top_z)
        if backpack:
            pack = material(f"{n}_backpack", backpack, 0.7, sheen=0.3)
            shapes.box(f, f"{n}_backpack", (r0 * 1.5, r0 * 0.7, d["spine"] * 0.62),
                       (0, r0 * 0.74 + r0 * 0.3, d["spine"] * 0.5), mat=pack, parent=self.breath, bevel=0.03)

        self._keyed = [(self.pelvis, ("location", "rotation_euler"), DELAY["pelvis"]),
                       (self.spine, ("rotation_euler",), DELAY["spine"]),
                       (self.neck, ("rotation_euler",), DELAY["neck"])]
        for side in ("r", "l"):
            self._keyed += [(self.shoulder[side], ("rotation_euler",), DELAY["shoulder"]),
                            (self.elbow[side], ("rotation_euler",), DELAY["elbow"]),
                            (self.wrist[side], ("rotation_euler",), DELAY["wrist"]),
                            (self.hip[side], ("rotation_euler",), DELAY["leg"]),
                            (self.knee[side], ("rotation_euler",), DELAY["leg"]),
                            (self.ankle[side], ("rotation_euler",), DELAY["leg"]),
                            (self.brow[side], ("location", "rotation_euler"), DELAY["face"]),
                            (self.lid[side], ("rotation_euler",), DELAY["face"]),
                            (self.eye[side], ("rotation_euler",), DELAY["face"])]
        self._keyed.append((self.mouth, ("location", "rotation_euler", "scale"), DELAY["face"]))
        if self.glasses_pivot is not None:
            self._keyed.append((self.glasses_pivot, ("location", "rotation_euler"), DELAY["glasses"]))
        self._apply({})

    # --------------------------------------------------------------- building

    def _torso_radius(self, z):
        """Torso radius at height z (spine space), used to place things on the chest."""
        r0, r1 = self.d["torso"]
        top_z, bot_z = self.d["spine"] - r0 * 0.5, r1 * 0.55
        if z >= top_z:
            return math.sqrt(max(0.0, r0 * r0 - (z - top_z) ** 2))
        if z <= bot_z:
            return math.sqrt(max(0.0, r1 * r1 - (z - bot_z) ** 2))
        return r1 + (r0 - r1) * (z - bot_z) / (top_z - bot_z)

    def _dress_top(self, top, mats, inner, r0, r1, top_z, bot_z, hr):
        f, n, d = self.film, self.name, self.d
        front0 = -r0 * 0.74
        if top == "hoodie":
            hood = [(math.cos(a) * hr * 0.62, math.sin(a) * hr * 0.55 + r0 * 0.12, d["spine"] - 0.005)
                    for a in [i * math.pi / 10 for i in range(11)]]
            shapes.tube(f, f"{n}_hood", hood, hr * 0.28, mat=mats["shirt"], parent=self.spine)
            shapes.sphere(f, f"{n}_pocket", 1, (0, -r1 * 0.74 - 0.004, bot_z + (top_z - bot_z) * 0.15),
                          (r1 * 0.75, 0.012, (top_z - bot_z) * 0.25), mats["shirt"], self.breath)
            string = material("hoodie_string", "#f2f2f2", 0.7)
            for sx in (-1, 1):
                z0 = d["spine"] - r0 * 0.35
                fy = [-(self._torso_radius(z) * 0.74 + 0.006) for z in (z0, z0 - d["spine"] * 0.18, z0 - d["spine"] * 0.3)]
                shapes.tube(f, f"{n}_string_{sx}", [(sx * hr * 0.2, fy[0], z0),
                                                     (sx * hr * 0.22, fy[1], z0 - d["spine"] * 0.18),
                                                     (sx * hr * 0.21, fy[2], z0 - d["spine"] * 0.3)],
                            0.006 * (d["head"] / 0.165), mat=string, parent=self.breath)
        elif top == "cardigan":
            m_inner = mats["inner"]
            z = top_z - r0 * 0.05
            shapes.sphere(f, f"{n}_blouse", 1, (0, -self._torso_radius(z) * 0.74 + 0.004, z),
                          (r0 * 0.17, 0.012, r0 * 0.42), m_inner, self.breath)
            button = material("button", "#e8dcc0", 0.4, coat=0.5)
            for i in range(3):
                z = bot_z + (top_z - bot_z) * (0.2 + 0.28 * i)
                shapes.sphere(f, f"{n}_button", r0 * 0.07, (0, -r0 * 0.78, z), mat=button, parent=self.breath,
                              segments=10, rings=6)
        elif top == "suit":
            z = top_z - r0 * 0.12
            shapes.sphere(f, f"{n}_shirtfront", 1, (0, -self._torso_radius(z) * 0.74 + 0.004, z),
                          (r0 * 0.21, 0.012, r0 * 0.5), mats["inner"], self.breath)

    def _build_head(self, mats, hair_style, cap, cap_backwards, sunglasses, glasses, mustache):
        f, n, hr = self.film, self.name, self.hr
        c = hr * 0.92  # head center above the head pivot
        H = self.head
        S = shapes.sphere
        S(f, f"{n}_skull", hr, (0, 0, c), (1, 0.97, 1.03), mats["skin"], H)
        S(f, f"{n}_cheeks", hr * 0.78, (0, -hr * 0.13, c - hr * 0.3), (1.0, 0.92, 0.85), mats["skin"], H)
        S(f, f"{n}_nose", hr * 0.13, (0, -hr * 1.0, c - hr * 0.1), (0.9, 1, 1.1), mats["skin"], H)
        for sx in (-1, 1):
            S(f, f"{n}_ear", hr * 0.24, (sx * hr * 0.97, hr * 0.05, c - hr * 0.05), (0.42, 0.8, 1.0),
              mats["skin"], H)

        self.blink, self.eye, self.lid, self.brow = {}, {}, {}, {}
        for side, sx in (("r", -1), ("l", 1)):
            blink = shapes.empty(f, f"{n}_blink_{side}", (sx * hr * 0.36, -hr * 0.82, c + hr * 0.08), H)
            eye = shapes.empty(f, f"{n}_eye_{side}", (0, 0, 0), blink)
            S(f, f"{n}_eyeball_{side}", hr * 0.24, mat=mats["white"], parent=eye, segments=24, rings=12)
            S(f, f"{n}_iris_{side}", hr * 0.15, (0, -hr * 0.2, 0), (1, 0.35, 1), mats["iris"], eye,
              segments=20, rings=10)
            S(f, f"{n}_pupil_{side}", hr * 0.075, (0, -hr * 0.235, 0), (1, 0.3, 1), mats["pupil"], eye,
              segments=16, rings=8)
            S(f, f"{n}_shine_{side}", hr * 0.03, (hr * 0.05, -hr * 0.25, hr * 0.05), mat=mats["shine"],
              parent=eye, segments=8, rings=6)
            lid = shapes.empty(f, f"{n}_lid_{side}", (0, 0, 0), blink)
            S(f, f"{n}_lidshape_{side}", hr * 0.265, mat=mats["skin"], parent=lid, cut_below=-0.02,
              segments=24, rings=12)
            brow = shapes.empty(f, f"{n}_brow_{side}", (sx * hr * 0.36, -hr * 0.88, c + hr * 0.4), H)
            inner = -sx
            shapes.tube(f, f"{n}_browshape_{side}",
                        [(inner * hr * 0.17, 0, -hr * 0.01), (0, -hr * 0.01, hr * 0.03), (-inner * hr * 0.18, 0, -hr * 0.02)],
                        [hr * 0.055, hr * 0.05, hr * 0.03], mat=mats["hair"], parent=brow)
            self.blink[side], self.eye[side], self.lid[side], self.brow[side] = blink, eye, lid, brow
        self.brow_z = c + hr * 0.4

        # mouth: lips (shape = smile/frown/smirk) and an opening for talking
        self.mouth_base = Vector((0, -hr * 0.9, c - hr * 0.42))
        self.mouth = shapes.empty(f, f"{n}_mouth", self.mouth_base, H)
        lips = []
        for i in range(9):
            u = -1 + 2 * i / 8
            lips.append((hr * 0.3 * u, hr * 0.1 * u * u, hr * 0.09 * u * u))
        radii = [hr * (0.022 + 0.02 * (1 - abs(-1 + 2 * i / 8))) for i in range(9)]
        shapes.tube(f, f"{n}_lips", lips, radii, mat=mats["lips"], parent=self.mouth)
        self.mouth_open = S(f, f"{n}_mouthopen", 1, (0, -hr * 0.87, c - hr * 0.5), (hr * 0.2, hr * 0.06, 0.001),
                            mats["mouth"], H, segments=16, rings=8)

        # hair
        hair = mats["hair"]
        hairline = lambda x, y, z: z > 0.05 + 0.45 * (-y)  # noqa: E731  (higher in front, lower behind)
        if hair_style in ("short", "buzz", "long", "ponytail", "bun"):
            S(f, f"{n}_hair", hr * (1.025 if hair_style == "buzz" else 1.06), (0, hr * 0.02, c + hr * 0.02),
              mat=hair, parent=H, keep=hairline)
        if hair_style == "short":
            S(f, f"{n}_tuft", hr * 0.38, (hr * 0.15, -hr * 0.55, c + hr * 0.78), (1.4, 0.8, 0.55), hair, H)
        elif hair_style == "long":
            S(f, f"{n}_hairback", 1, (0, hr * 0.38, c - hr * 0.4), (hr * 1.04, hr * 0.6, hr * 1.25), hair, H)
        elif hair_style == "bun":
            S(f, f"{n}_bun", hr * 0.42, (0, hr * 0.72, c + hr * 0.62), mat=hair, parent=H)
        elif hair_style == "ponytail":
            pivot = shapes.empty(f, f"{n}_ponytail", (0, hr * 0.98, c + hr * 0.25), H)
            shapes.capsule(f, f"{n}_tail", hr * 0.24, hr * 0.12, hr * 1.0, (0, 0, -hr * 0.05), hair, pivot)
            S(f, f"{n}_hairtie", hr * 0.16, (0, 0, -hr * 0.02), (1.2, 1.2, 0.6),
              material("hairtie", "#ff4f8b", 0.4), pivot)
            self.springs.append(dict(pivot=pivot, length=hr * 1.0, stiffness=60, damping=7))
        elif hair_style == "bald":
            S(f, f"{n}_sidehair", hr * 1.04, (0, hr * 0.02, c), mat=hair, parent=H,
              keep=lambda x, y, z: -0.45 < z < 0.2 and y > -0.35)

        if cap:
            m_cap = material(f"{n}_cap", cap, 0.7, sheen=0.4)
            S(f, f"{n}_capdome", hr * 1.1, (0, 0, c + hr * 0.03), mat=m_cap, parent=H,
              keep=lambda x, y, z: z > 0.22)
            by = hr * 1.0 * (1 if cap_backwards else -1)
            S(f, f"{n}_capbrim", 1, (0, by, c + hr * 0.25), (hr * 0.62, hr * 0.58, hr * 0.045), m_cap, H)
            S(f, f"{n}_capbutton", hr * 0.08, (0, 0, c + hr * 1.12), mat=m_cap, parent=H, segments=10, rings=6)

        self.glasses_pivot = None
        if sunglasses or glasses:
            self.glasses_base = Vector((0, -hr * 1.13, c + hr * 0.1))
            gp = shapes.empty(f, f"{n}_glasses", self.glasses_base, H)
            self.glasses_pivot = gp
            frame_mat = material("shades_frame", "#111111", 0.25, coat=0.6) if sunglasses else \
                material(f"{n}_frames", glasses, 0.35, coat=0.5)
            for sx in (-1, 1):
                if sunglasses:
                    S(f, f"{n}_lens", hr * 0.28, (sx * hr * 0.36, 0, 0), (1.15, 0.22, 0.78),
                      material("shades_lens", "#0a0a0c", 0.05, coat=1.0), gp)
                else:
                    ring = [(sx * hr * 0.36 + math.cos(a) * hr * 0.25, 0, math.sin(a) * hr * 0.2)
                            for a in [i * 2 * math.pi / 16 for i in range(16)]]
                    shapes.tube(f, f"{n}_rim", ring, hr * 0.022, mat=frame_mat, parent=gp, closed=True)
                shapes.tube(f, f"{n}_arm", [(sx * hr * 0.64, 0.0, hr * 0.04), (sx * hr * 0.95, hr * 0.5, hr * 0.03),
                                            (sx * hr * 0.99, hr * 1.18, -hr * 0.02)], hr * 0.022, mat=frame_mat, parent=gp)
            shapes.tube(f, f"{n}_bridge", [(-hr * 0.1, 0, hr * 0.03), (0, -hr * 0.02, hr * 0.07), (hr * 0.1, 0, hr * 0.03)],
                        hr * 0.025, mat=frame_mat, parent=gp)

        if mustache:
            shapes.tube(f, f"{n}_mustache", [(-hr * 0.3, hr * 0.06, c - hr * 0.36), (-hr * 0.12, -hr * 0.02, c - hr * 0.26),
                                             (0, -hr * 0.04, c - hr * 0.25), (hr * 0.12, -hr * 0.02, c - hr * 0.26),
                                             (hr * 0.3, hr * 0.06, c - hr * 0.36)],
                        [hr * 0.03, hr * 0.07, hr * 0.075, hr * 0.07, hr * 0.03], mat=hair,
                        location=(0, -hr * 0.93, 0), parent=H)

    def _build_chain(self, r0, top_z):
        f, n, hr, d = self.film, self.name, self.hr, self.d
        gold = material("gold", "#f2c14e", 0.22, metallic=1.0)
        z0 = d["spine"] - 0.03
        drop = d["spine"] * 0.3
        pts = []
        for i in range(32):
            a = 2 * math.pi * i / 32
            front = max(0.0, -math.sin(a))
            z = z0 - front ** 2 * drop
            r = self._torso_radius(z) + 0.006
            pts.append((math.cos(a) * r, math.sin(a) * r * 0.74 - front * 0.004, z))
        shapes.tube(f, f"{n}_chain", pts, 0.006 * hr / 0.165, mat=gold, parent=self.breath, closed=True, segments=6)
        front_y = -(self._torso_radius(z0 - drop) + 0.006) * 0.74
        pend = shapes.empty(f, f"{n}_pendant", (0, front_y - 0.004, z0 - drop), self.spine)
        shapes.cylinder(f, f"{n}_medal", hr * 0.2, hr * 0.05, (0, -hr * 0.04, -hr * 0.2), (math.pi / 2, 0, 0),
                        mat=gold, parent=pend)
        shapes.text(f, f"{n}_dollar", "$", hr * 0.3, (0, -hr * 0.07, -hr * 0.21), mat=material("gold_dark", "#b8860b", 0.3, metallic=1.0),
                    parent=pend, depth=hr * 0.02)
        self.springs.append(dict(pivot=pend, length=hr * 0.2, stiffness=45, damping=5))

    def _build_tie(self, tie, r0, top_z):
        f, n, d = self.film, self.name, self.d
        m = material(f"{n}_tie", tie, 0.5, sheen=0.4)
        z0 = d["spine"] - r0 * 0.3
        y0 = -self._torso_radius(z0) * 0.74 - 0.008
        shapes.sphere(f, f"{n}_tieknot", r0 * 0.085, (0, y0, z0), (1, 0.6, 0.85), m, self.breath)
        y1 = -self._torso_radius(z0 - d["spine"] * 0.3) * 0.74 - 0.008
        tie_obj = shapes.capsule(f, f"{n}_tie", r0 * 0.075, r0 * 0.12, d["spine"] * 0.42, (0, y0, z0 - r0 * 0.06),
                                 m, self.breath, scale=(1, 0.22, 1))
        tie_obj.rotation_euler = (math.atan2(y1 - y0, d["spine"] * 0.3), 0, 0)

    # ------------------------------------------------------------------ state

    def forward(self):
        return Vector((math.sin(self.angle), -math.cos(self.angle), 0.0))

    def position(self):
        return Vector((self.x, self.y, 0.0))

    def _seat_drop(self):
        return self.seated["hips"]["bob"] if self.seated else 0.0

    def head_position(self):
        return Vector((self.x, self.y, (self.head_center + self._seat_drop()) * self.scale))

    def height(self):
        return (self.head_center + self.hr + self._seat_drop()) * self.scale

    def _angle_to(self, target):
        p = _point(target)
        dx, dy = p.x - self.x, p.y - self.y
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return self.angle
        return _unwrap(self.angle, math.atan2(dx, -dy))

    # ------------------------------------------------------------- posing

    def _solve_leg(self, side, target, pitch=0.0, yaw=0.0):
        """Bends hip, knee and ankle so the ankle reaches `target` (root space) with the foot flat."""
        d = self.d
        rot_p = self.pelvis.rotation_euler.to_matrix()
        m_p = Matrix.Translation(self.pelvis.location) @ rot_p.to_4x4()
        v = (m_p.inverted() @ target) - self.hip[side].location
        a, b = d["thigh"], d["shin"]
        dist = _clamp(v.length, abs(a - b) + 1e-3, (a + b) * 0.9995)
        knee = math.pi - math.acos(_clamp((a * a + b * b - dist * dist) / (2 * a * b), -1, 1))
        phi = math.atan2(b * math.sin(knee), a + b * math.cos(knee))
        theta = math.atan2(v.y, math.sqrt(v.x * v.x + v.z * v.z))
        beta = math.atan2(-v.x, -v.z)
        hip_rot = Euler((theta - phi, beta, 0.0))
        knee_rot = Euler((knee, 0.0, 0.0))
        self.hip[side].rotation_euler = hip_rot
        self.knee[side].rotation_euler = knee_rot
        total = rot_p @ hip_rot.to_matrix() @ knee_rot.to_matrix()
        foot = Matrix.Rotation(yaw, 3, "Z") @ Matrix.Rotation(pitch, 3, "X")
        self.ankle[side].rotation_euler = (total.inverted() @ foot).to_euler("XYZ")

    def _apply(self, pose):
        d = self.d
        body = pose.get("body", {})
        hips = pose.get("hips", {})
        bob = hips.get("bob", body.get("bob", 0.0))
        sway = hips.get("sway", body.get("sway", 0.0))
        self.pelvis.location = (-sway, hips.get("shift", 0.0), self.P + bob)
        self.pelvis.rotation_euler = (_rad(hips.get("tilt_forward", 0)), _rad(hips.get("tilt", 0)),
                                      _rad(hips.get("twist", 0)))
        self.spine.rotation_euler = (_rad(body.get("lean", 0)), _rad(body.get("side", 0)), _rad(body.get("twist", 0)))
        head = pose.get("head", {})
        self.neck.rotation_euler = (_rad(head.get("nod", 0)), _rad(head.get("tilt", 0)), _rad(head.get("turn", 0)))

        for side, sign in (("r", 1), ("l", -1)):
            arm = pose.get("arm_" + side, {})
            self.shoulder[side].rotation_euler = (_rad(-arm.get("forward", 0)), _rad(sign * (arm.get("out", 0) + 6)),
                                                  _rad(sign * arm.get("twist", 0)))
            self.elbow[side].rotation_euler = (_rad(-(arm.get("bend", 0) + 8)), 0, 0)
            self.wrist[side].rotation_euler = (_rad(-arm.get("wrist", 0)), 0, 0)

        feet = pose.get("_feet")
        free = pose.get("feet") == "free"
        stance = pose.get("stance", 0.0)
        for side, sx in (("r", -1), ("l", 1)):
            leg = pose.get("leg_" + side)
            if feet is not None:
                target, pitch, yaw = feet[side]
                self._solve_leg(side, target, pitch, yaw)
            elif free or leg is not None:
                leg = leg or {}
                self.hip[side].rotation_euler = (_rad(-leg.get("forward", 0)), _rad(-sx * leg.get("out", 0)), 0)
                self.knee[side].rotation_euler = (_rad(leg.get("bend", 0)), 0, 0)
                self.ankle[side].rotation_euler = (_rad(leg.get("point", 0)), 0, 0)
            else:
                target = Vector((sx * (d["hip_w"] + stance), 0.0, d["ankle"]))
                self._solve_leg(side, target)

        face = dict(self.face_state, **pose.get("face", {}))
        brows = pose.get("brows", {})
        lid_angle = _rad(95) + (_rad(-50) - _rad(95)) * _clamp(face["lids"], 0, 1)
        look = face["look"]
        for side, sx in (("r", -1), ("l", 1)):
            self.lid[side].rotation_euler = (lid_angle, 0, 0)
            self.eye[side].rotation_euler = (_rad(-look[1]), 0, _rad(look[0]))
            raise_ = brows.get("raise", 0.0) * (self.hr / 0.165) + face["brow_raise"] * self.hr
            self.brow[side].location.z = self.brow_z + raise_
            self.brow[side].rotation_euler = (0, _rad(sx * (brows.get("angle", 0) + face["brow_angle"])), 0)
        smile, smirk = face["smile"], face["smirk"]
        curve = 0.15 + 0.85 * smile if smile >= 0 else 0.15 + 1.05 * smile
        if abs(curve) < 0.05:
            curve = 0.05
        self.mouth.scale = (1.0, 1.0, curve)
        self.mouth.rotation_euler = (0, _rad(-16 * smirk), 0)
        self.mouth.location = self.mouth_base + Vector((self.hr * 0.1 * smirk, 0, self.hr * 0.03 * abs(smirk)))
        if self.glasses_pivot is not None:
            g = face["glasses"]
            self.glasses_pivot.location = self.glasses_base + Vector((0, -self.hr * 0.06 * g, -self.hr * 0.4 * g))
            self.glasses_pivot.rotation_euler = (_rad(-14 * g), 0, 0)

    def _key(self, t, pose, delays=True):
        self._apply(pose)
        for obj, paths, delay in self._keyed:
            frame = self.film.frame(t + (delay if delays else 0.0))
            for path in paths:
                obj.keyframe_insert(path, frame=frame)

    def _key_root(self, t, what=("location", "rotation_euler")):
        self.root.location = (self.x, self.y, 0)
        self.root.rotation_euler = (0, 0, self.angle)
        for path in what:
            self.root.keyframe_insert(path, frame=self.film.frame(t))

    def _hold(self, t):
        """Pins the current pose and position at time t, so the next action starts from here."""
        self._key(t, self.current_pose)
        self._key_root(t)

    def _play_from(self, t, move, times=None):
        if isinstance(move, str):
            if move not in MOVES:
                raise ValueError(f"No move called {move!r}. Moves: {', '.join(sorted(MOVES))}")
            move = MOVES[move]
        self._key(t, self.current_pose)
        base = self.seated or {}
        last = {}
        for _ in range(times or move.get("repeat", 1)):
            for step in move["steps"]:
                seconds, pose = step[0], step[1]
                if base:  # sitting: keep the legs and hips of the seated pose
                    pose = dict(pose, **{k: v for k, v in base.items() if k in ("feet", "hips", "leg_r", "leg_l")})
                t += seconds
                self._key(t, pose)
                if len(step) > 2 and step[2] > 0:
                    t += step[2]
                    self._key(t, pose)
                last = pose
        if move.get("stay"):
            self.current_pose = last
        else:
            t += move.get("settle", 0.35)
            self._key(t, base)
            self.current_pose = dict(base)
        return t

    def _turn_from(self, t, new_angle):
        """Turns the body with the head leading. Returns when the turn ends."""
        delta = new_angle - self.angle
        if abs(delta) < 0.05:
            return t
        seconds = 0.22 + 0.3 * abs(delta) / math.pi
        lead = dict(self.current_pose)
        lead["head"] = dict(lead.get("head", {}), turn=_clamp(math.degrees(delta) * 0.6, -55, 55))
        lead["hips"] = dict(lead.get("hips", {}), bob=-0.015)
        self._key(t + seconds * 0.35, lead, delays=False)
        self.angle = new_angle
        self._key_root(t + seconds, ("rotation_euler",))
        self._key(t + seconds, self.current_pose)
        return t + seconds

    # ------------------------------------------------------------------ actions
    # Each action starts at the film's current time and moves the clock forward
    # (inside `with film.together():` each character keeps its own clock).

    def place(self, x, y, face=None):
        """Puts the character somewhere instantly (use at the start or on a cut)."""
        t = self.film._start(self)
        # Pin where we were just before the jump (only once if placed several times at the same moment).
        if t > 0 and getattr(self, "_placed_at", None) != t:
            self._key(t - 1 / self.film.fps, self.current_pose, delays=False)
            self._key_root(t - 1 / self.film.fps)
        self._placed_at = t
        self.x, self.y = x, y
        if face is not None:
            self.angle = self._angle_to(face)
        self.current_pose = {}
        self._key(t, {}, delays=False)
        self._key_root(t)
        self.film._end(self, t)

    def face(self, target, seconds=None):
        """Turns the whole body toward a spot (x, y) or another character (head leads)."""
        t = self.film._start(self)
        self._hold(t)
        self.film._end(self, self._turn_from(t, self._angle_to(target)))

    def look_at(self, target, seconds=0.4):
        """Turns just the head (up/down too) toward a spot or character. Stays until the next move."""
        t = self.film._start(self)
        self._hold(t)
        p = _point(target)
        to = p - self.head_position()
        flat = Vector((to.x, to.y, 0))
        turn = math.degrees(_unwrap(0, math.atan2(to.x, -to.y) - self.angle)) if flat.length > 1e-3 else 0
        nod = -math.degrees(math.atan2(to.z, max(flat.length, 1e-3)))
        pose = dict(self.current_pose)
        pose["head"] = {"turn": _clamp(turn, -75, 75), "nod": _clamp(nod, -40, 40)}
        self.current_pose = pose
        t += seconds
        self._key(t, pose)
        self.film._end(self, t)

    def pose(self, pose, seconds=0.4, hold=0.0):
        """Moves into a custom pose and keeps it until the next move."""
        t = self.film._start(self)
        self._hold(t)
        self.current_pose = pose
        t += seconds
        self._key(t, pose)
        t += hold
        self.film._end(self, t)

    def wait(self, seconds):
        """This character waits (useful inside `with film.together():` to time a line)."""
        t = self.film._start(self)
        self._hold(t)
        self.film._end(self, t + seconds)

    def rest(self, seconds=0.4):
        self.pose({}, seconds)

    def set_face(self, seconds=0.3, **face):
        """Changes the default expression from now on, e.g. set_face(smirk=0.6, lids=0.55).
        Keys: lids (0 closed - 1 wide open), smile (-1 frown - 1 big smile), smirk (-1..1),
        look=(right/left degrees, up/down degrees), glasses (0 on - 1 lowered), brow_raise, brow_angle."""
        t = self.film._start(self)
        self._hold(t)
        self.face_state.update(face)
        t += seconds
        self._key(t, self.current_pose)
        self.film._end(self, t)

    def sit(self, seat_height, seconds=0.6):
        """Sits down on something seat_height meters tall (a bench, a crate, a chair). Stays seated."""
        drop = seat_height / self.scale + 0.03 - self.P
        pose = {"feet": "free", "hips": {"bob": drop, "shift": 0.06},
                "leg_r": {"forward": 85, "bend": 88, "out": 6}, "leg_l": {"forward": 85, "bend": 88, "out": 6},
                "arm_r": {"forward": 20, "bend": 30}, "arm_l": {"forward": 20, "bend": 30}, "body": {"lean": 4}}
        self.seated = pose
        self.pose(pose, seconds)

    def stand(self, seconds=0.6):
        self.seated = None
        self.pose({}, seconds)

    def play(self, move, times=None):
        """Plays a move from the library, e.g. "wave", "jump", "dance"."""
        t = self.film._start(self)
        self._key_root(t)
        self.film._end(self, self._play_from(t, move, times))

    def say(self, text, seconds=None, gesture=None):
        """Says a line: subtitles + a talking mouth. gesture plays a move at the same time."""
        t = self.film._start(self)
        seconds = seconds or (1.1 + 0.065 * len(text))
        self.film._subtitle(t, t + seconds, self.name, text)
        self.talking.append((t, t + seconds))

        rng = random.Random(f"{self.name}{text}")
        f = self.film.frame
        mo = self.mouth_open
        closed = mo.scale.copy()
        mo.keyframe_insert("scale", frame=f(t))
        tt = t + 0.06
        words = text.split()
        while tt < t + seconds - 0.25:
            mo.scale = (closed.x * rng.uniform(0.85, 1.15), closed.y, self.hr * rng.uniform(0.06, 0.13))
            mo.keyframe_insert("scale", frame=f(tt))
            tt += rng.uniform(0.07, 0.12)
            mo.scale = (closed.x, closed.y, self.hr * rng.uniform(0.005, 0.03))
            mo.keyframe_insert("scale", frame=f(tt))
            tt += rng.uniform(0.06, 0.1)
            if words and rng.random() < 0.12:
                tt += 0.12  # little pause between phrases
        mo.scale = closed
        mo.keyframe_insert("scale", frame=f(t + seconds))

        end = t + seconds
        if gesture:
            self._key_root(t)
            end = max(end, self._play_from(t, gesture))
        self.film._end(self, end)

    # -------------------------------------------------------------- walking

    def walk_to(self, x, y, speed=None, style="normal", run=False):
        """Walks with planted feet. style: "normal", "swagger", "run" or "sneak"."""
        if run:
            style = "run"
        st = WALK_STYLES[style]
        t = self.film._start(self)
        self._hold(t)
        start = self.position()
        target = Vector((x, y, 0.0))
        dist = (target - start).length
        if dist < 0.02:
            self.film._end(self, t)
            return
        t = self._turn_from(t, self._angle_to(target))
        self._hold(t)

        k = self.scale
        leg = self.leg_len * k
        speed = speed or st["speed"] * math.sqrt(leg)
        step_max = st["step"] * leg
        n_steps = max(1, math.ceil(dist / step_max))
        L = dist / n_steps
        accel = min(0.4, dist / speed / 2.5)
        duration = dist / speed + accel
        direction = (target - start).normalized()
        perp = Vector((-direction.y, direction.x, 0.0))  # to the character's left
        w = self.d["hip_w"] * k * 1.05

        # Footstep plan: each step is (foot, from_d, to_d, lift_s, land_s) along the path.
        steps, last = [], {"r": 0.0, "l": 0.0}
        for i in range(1, n_steps + 1):
            foot = "r" if i % 2 else "l"
            land = min(dist, (i - 0.5) * L) if i < n_steps else dist - 0.5 * L
            lift = max(0.0, (i - 1.5) * L + 0.12 * L)
            steps.append((foot, last[foot], i * L, lift, max(land, lift + 0.05 * L)))
            last[foot] = i * L
        other = "l" if n_steps % 2 else "r"
        steps.append((other, last[other], dist, max(0.0, dist - 0.42 * L), dist))

        def s_at(tt):
            v = dist / (duration - accel)
            if tt <= 0:
                return 0.0
            if tt >= duration:
                return dist
            if tt < accel:
                return 0.5 * v * tt * tt / accel
            if tt > duration - accel:
                r = duration - tt
                return dist - 0.5 * v * r * r / accel
            return 0.5 * v * accel + v * (tt - accel)

        def feet_at(s):
            out = {}
            swing = None
            for foot in ("r", "l"):
                pos, lift_h, pitch = 0.0, 0.0, 0.0
                for (fo, a, b, s0, s1) in steps:
                    if fo != foot:
                        continue
                    if s >= s1:
                        pos = b
                    elif s > s0:
                        u = (s - s0) / (s1 - s0)
                        e = u * u * (3 - 2 * u)
                        pos = a + (b - a) * e
                        lift_h = st["lift"] * leg * math.sin(math.pi * u)
                        pitch = _rad(25) * math.sin(math.pi * u) * (1 - 2 * u)
                        swing = (foot, u)
                        break
                    else:
                        pos = a
                        break
                out[foot] = (pos, lift_h, pitch)
            return out, swing

        f0 = math.ceil(self.film.frame(t))
        f1 = math.floor(self.film.frame(t + duration))
        rot_inv = Matrix.Rotation(-self.angle, 3, "Z")
        with self.film.linear_keys():
            for frame in range(f0, f1 + 1):
                tt = (frame - 1) / self.film.fps - t
                s = s_at(tt)
                root = start + direction * s
                feet, swing = feet_at(s)
                lag_feet, _ = feet_at(max(0.0, s - 0.1 * speed))
                local = {}
                for foot, sx in (("r", -1), ("l", 1)):
                    along, lift_h, pitch = feet[foot]
                    world = start + direction * along + perp * (sx * w)
                    p = rot_inv @ (world - root) / k
                    local[foot] = (Vector((p.x, p.y, self.d["ankle"] + lift_h / k)), pitch, 0.0)

                u = swing[1] if swing else 0.0
                lift_phase = math.sin(math.pi * u)
                bob = st["bob"] * self.leg_len * (lift_phase - 0.3) - st["crouch"] * self.leg_len
                sway_dir = (1 if swing and swing[0] == "l" else -1) if swing else 0
                sway = st["sway"] * self.leg_len * lift_phase * sway_dir
                ahead = _clamp((feet["r"][0] - feet["l"][0]) / max(L, 1e-3), -1, 1)  # + when the right foot leads
                ahead_lag = _clamp((lag_feet["r"][0] - lag_feet["l"][0]) / max(L, 1e-3), -1, 1)
                twist = st["twist"] * ahead
                spine_twist = -st["counter"] * twist
                # keep the hips low enough that both feet can reach the ground
                z = self.P + bob
                for foot, sx in (("r", -1), ("l", 1)):
                    target = local[foot][0]
                    hx = -sway + sx * self.d["hip_w"]
                    hd = math.hypot(target.x - hx, target.y)
                    reach = 0.985 * self.leg_len
                    if hd < reach:
                        z = min(z, target.z + math.sqrt(reach * reach - hd * hd) + self.d["hip_drop"])
                bob = z - self.P
                ramp = min(1.0, s / max(L * 0.5, 1e-3), (dist - s) / max(L * 0.5, 1e-3) + 0.3)
                arm = st["arm"] * ahead_lag * ramp
                pose = {
                    "hips": {"bob": bob, "sway": sway, "twist": twist * ramp},
                    "body": {"lean": st["lean"] * min(1.0, ramp * 2), "twist": spine_twist * ramp,
                             "side": -sway_dir * lift_phase * (4 if style == "swagger" else 1.5)},
                    "head": {"turn": -(twist + spine_twist) * ramp, "nod": -st["lean"] * 0.4 +
                             st["head_bob"] * (0.5 - lift_phase) * ramp},
                    "arm_r": {"forward": -arm, "bend": st["elbow"] + max(0.0, -arm) * 0.4, "out": st["out"]},
                    "arm_l": {"forward": arm, "bend": st["elbow"] + max(0.0, arm) * 0.4, "out": st["out"]},
                    "_feet": local,
                }
                self.x, self.y = root.x, root.y
                self.root.location = (root.x, root.y, 0)
                self.root.keyframe_insert("location", frame=frame)
                self._apply(pose)
                for obj, paths, _ in self._keyed:
                    for path in paths:
                        obj.keyframe_insert(path, frame=frame)

        t += duration
        self.x, self.y = x, y
        self._key_root(t)
        self.current_pose = {}
        t += 0.3
        self._key(t, {})
        self.film._end(self, t)

    def run_to(self, x, y):
        self.walk_to(x, y, style="run")

    # ------------------------------------------------------------ handling props

    def hold(self, obj, hand="r"):
        """The object follows this character's hand from now on."""
        self.film._attach(obj, self, hand, self.film._start(self))

    def give(self, obj, other, hand="r"):
        """Hands an object to another character (both reach out, it changes hands)."""
        film = self.film
        t = max(film._start(self), film._start(other))
        self._hold(t)
        other._hold(t)
        if film._holder(obj) is not self:
            film._attach(obj, self, hand, t)
        reach = {"arm_" + hand: {"forward": 58, "out": -6, "bend": 22, "wrist": -10}, "body": {"lean": 6}}
        take = {"arm_r": {"forward": 55, "out": -4, "bend": 25, "wrist": -10}, "body": {"lean": 6}}
        self._key(t + 0.4, dict(self.current_pose, **reach))
        other._key(t + 0.5, dict(other.current_pose, **take))
        film._attach(obj, other, "r", t + 0.62)
        self._key(t + 0.95, self.current_pose)
        other._key(t + 1.05, other.current_pose)
        film._end(self, t + 1.05)
        film._end(other, t + 1.05)

    def pocket(self, obj):
        """Puts an object away (it disappears into a pocket)."""
        t = self.film._start(self)
        self._hold(t)
        side = "r"
        self._key(t + 0.3, dict(self.current_pose, **{"arm_" + side: {"forward": -10, "out": 4, "bend": 35}}))
        self.film._hide_at(obj, t + 0.32)
        self._key(t + 0.6, self.current_pose)
        self.film._end(self, t + 0.6)

    # ------------------------------------------------------------ automatic life

    def _add_life(self, length):
        """Breathing, idle head motion, eye darts and blinks for the whole film."""
        rng = random.Random(self.name)
        f = self.film.frame
        # breathing
        t = 0.0
        while t < length + 1:
            b = math.sin(2 * math.pi * t / 3.4)
            self.breath.scale = (1 + 0.012 * b, 1 + 0.02 * b, 1 + 0.006 * b)
            self.breath.keyframe_insert("scale", frame=f(t))
            t += 0.85
        # small head motion, bigger while talking
        t = 0.0
        while t < length + 1:
            talking = any(a <= t <= b for a, b in self.talking)
            amp = 4.5 if talking else 2.0
            self.head.rotation_euler = (_rad(rng.uniform(-amp, amp * 0.6)), _rad(rng.uniform(-amp, amp) * 0.5),
                                        _rad(rng.uniform(-amp, amp)))
            self.head.keyframe_insert("rotation_euler", frame=f(t))
            t += rng.uniform(0.35, 0.6) if talking else rng.uniform(1.0, 1.8)
        # eye darts (quick moves, then hold)
        t = rng.uniform(0.5, 1.5)
        prev = (0.0, 0.0)
        while t < length:
            new = (_rad(rng.uniform(-6, 6)), _rad(rng.uniform(-3, 3)))
            for blink in self.blink.values():
                blink.rotation_euler = (prev[1], 0, prev[0])
                blink.keyframe_insert("rotation_euler", frame=f(t))
                blink.rotation_euler = (new[1], 0, new[0])
                blink.keyframe_insert("rotation_euler", frame=f(t + 0.05))
            prev = new
            t += rng.uniform(1.2, 3.0)
        # blinks
        t = rng.uniform(0.4, 2.0)
        while t < length - 0.3:
            for dt, s in ((0.0, 1.0), (0.05, 0.08), (0.14, 1.0)):
                for blink in self.blink.values():
                    blink.scale = (1, 1, s)
                    blink.keyframe_insert("scale", frame=f(t + dt))
            t += rng.uniform(2.2, 4.8) if rng.random() > 0.15 else 0.35
