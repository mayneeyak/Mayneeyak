"""Cartoon characters built from code, with joints you can pose and keyframe."""

import math
import random

from mathutils import Vector

from . import shapes
from .materials import material
from .moves import MOVES

HIP_HEIGHT = 0.62
ARM_REST_OUT = 7  # degrees, so arms don't sink into the body


def _rad(deg):
    return math.radians(deg)


def _unwrap(current, target):
    """The target angle closest to current (so turns never spin the long way)."""
    return current + (target - current + math.pi) % (2 * math.pi) - math.pi


def _point(target):
    """Accepts a Character, (x, y) or (x, y, z) and returns a 3D Vector."""
    if isinstance(target, Character):
        return target.head_position()
    if len(target) == 2:
        return Vector((target[0], target[1], 0.0))
    return Vector(target)


class Character:
    """A cartoon character.

    Colors can be "#rrggbb" strings or RGB tuples. scale=0.8 makes a smaller character.
    """

    def __init__(self, film, name, skin="#f2c29b", shirt="#3d8bff", pants="#2c3e66",
                 shoes="#333333", hair="#5a3a1e", long_hair=False, scale=1.0):
        self.film = film
        self.name = name
        self.scale = scale
        self.subtitle_color = shirt
        self.x, self.y, self.angle = 0.0, 0.0, 0.0
        self.current_pose = {}
        film.characters.append(self)

        m_skin = material(f"{name}_skin", skin, roughness=0.5)
        m_shirt = material(f"{name}_shirt", shirt, roughness=0.6)
        m_pants = material(f"{name}_pants", pants, roughness=0.7)
        m_shoes = material(f"{name}_shoes", shoes, roughness=0.4)
        m_hair = material(f"{name}_hair", hair, roughness=0.6)
        m_white = material("eye_white", "#ffffff", roughness=0.15)
        m_pupil = material("eye_pupil", "#15100c", roughness=0.1)
        m_mouth = material("mouth", "#5a1f1f", roughness=0.4)

        E, S = shapes.empty, shapes.sphere
        f = film
        self.root = E(f, f"{name}")
        self.root.scale = (scale, scale, scale)
        self.hips = E(f, f"{name}_hips", (0, 0, HIP_HEIGHT), self.root)
        self.spine = E(f, f"{name}_spine", (0, 0, 0), self.hips)
        self.neck = E(f, f"{name}_neck", (0, 0, 0.58), self.spine)

        # Body
        S(f, f"{name}_torso", 1, (0, 0, 0.28), (0.26, 0.19, 0.36), m_shirt, self.spine)
        S(f, f"{name}_waist", 1, (0, 0, 0.04), (0.24, 0.18, 0.15), m_pants, self.spine)

        # Head and face
        S(f, f"{name}_head", 0.27, (0, 0, 0.25), mat=m_skin, parent=self.neck)
        S(f, f"{name}_nose", 0.04, (0, -0.268, 0.22), mat=m_skin, parent=self.neck)
        self.eyes = []
        self.brows = {}
        for side, x in (("r", -0.1), ("l", 0.1)):
            eye = E(f, f"{name}_eye_{side}", (x, -0.225, 0.29), self.neck)
            S(f, f"{name}_eyewhite_{side}", 0.068, mat=m_white, parent=eye)
            S(f, f"{name}_pupil_{side}", 0.038, (0, -0.048, 0), mat=m_pupil, parent=eye)
            self.eyes.append(eye)
            brow = E(f, f"{name}_brow_{side}", (x, -0.238, 0.385), self.neck)
            S(f, f"{name}_browshape_{side}", 1, scale=(0.065, 0.018, 0.016), mat=m_hair, parent=brow)
            self.brows[side] = brow
        self.mouth = E(f, f"{name}_mouth", (0, -0.25, 0.16), self.neck)
        S(f, f"{name}_mouthshape", 1, scale=(0.07, 0.03, 0.022), mat=m_mouth, parent=self.mouth)

        # Hair: a cap on top plus a back piece (longer for long hair)
        S(f, f"{name}_haircap", 0.29, (0, 0.015, 0.27), mat=m_hair, parent=self.neck, cut_below=0.52)
        if long_hair:
            S(f, f"{name}_hairback", 1, (0, 0.1, 0.13), (0.3, 0.2, 0.37), m_hair, self.neck)
        else:
            S(f, f"{name}_hairback", 1, (0, 0.08, 0.3), (0.285, 0.22, 0.22), m_hair, self.neck)

        # Arms and legs
        self.shoulder, self.elbow, self.hip = {}, {}, {}
        for side, sign in (("r", -1), ("l", 1)):
            sh = E(f, f"{name}_shoulder_{side}", (0.27 * sign, 0, 0.5), self.spine)
            S(f, f"{name}_upperarm_{side}", 1, (0, 0, -0.12), (0.065, 0.065, 0.15), m_shirt, sh)
            el = E(f, f"{name}_elbow_{side}", (0, 0, -0.26), sh)
            S(f, f"{name}_forearm_{side}", 1, (0, 0, -0.11), (0.055, 0.055, 0.13), m_skin, el)
            S(f, f"{name}_hand_{side}", 0.07, (0, 0, -0.25), mat=m_skin, parent=el)
            hp = E(f, f"{name}_hip_{side}", (0.11 * sign, 0, -0.02), self.hips)
            S(f, f"{name}_leg_{side}", 1, (0, 0, -0.27), (0.09, 0.09, 0.3), m_pants, hp)
            S(f, f"{name}_shoe_{side}", 1, (0, -0.05, -0.555), (0.1, 0.15, 0.065), m_shoes, hp)
            self.shoulder[side], self.elbow[side], self.hip[side] = sh, el, hp

        self._posed = [self.spine, self.neck, *self.shoulder.values(), *self.elbow.values(),
                       *self.hip.values(), *self.brows.values()]
        self._apply({})

    # ------------------------------------------------------------------ state

    def forward(self):
        return Vector((math.sin(self.angle), -math.cos(self.angle), 0.0))

    def position(self):
        return Vector((self.x, self.y, 0.0))

    def head_position(self):
        return Vector((self.x, self.y, 1.45 * self.scale))

    def _angle_to(self, target):
        p = _point(target)
        dx, dy = p.x - self.x, p.y - self.y
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return self.angle
        return _unwrap(self.angle, math.atan2(dx, -dy))

    # --------------------------------------------------------------- keyframes

    def _apply(self, pose):
        b = pose.get("body", {})
        self.spine.rotation_euler = (_rad(b.get("lean", 0)), _rad(b.get("side", 0)), _rad(b.get("twist", 0)))
        self.hips.location = (-b.get("sway", 0), 0, HIP_HEIGHT + b.get("bob", 0))
        h = pose.get("head", {})
        self.neck.rotation_euler = (_rad(h.get("nod", 0)), _rad(h.get("tilt", 0)), _rad(h.get("turn", 0)))
        for side, sign in (("r", 1), ("l", -1)):
            a = pose.get("arm_" + side, {})
            out = a.get("out", 0) + ARM_REST_OUT
            self.shoulder[side].rotation_euler = (_rad(-a.get("forward", 0)), _rad(sign * out),
                                                  _rad(sign * a.get("twist", 0)))
            self.elbow[side].rotation_euler = (_rad(-a.get("bend", 0)), 0, 0)
            leg = pose.get("leg_" + side, {})
            self.hip[side].rotation_euler = (_rad(-leg.get("forward", 0)), _rad(sign * leg.get("out", 0)), 0)
        br = pose.get("brows", {})
        for side, sign in (("r", -1), ("l", 1)):
            self.brows[side].location.z = 0.385 + br.get("raise", 0)
            self.brows[side].rotation_euler = (0, _rad(sign * br.get("angle", 0)), 0)

    def _key(self, t, pose):
        self._apply(pose)
        frame = self.film.frame(t)
        for obj in self._posed:
            obj.keyframe_insert("rotation_euler", frame=frame)
        self.hips.keyframe_insert("location", frame=frame)
        for brow in self.brows.values():
            brow.keyframe_insert("location", frame=frame)

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
        last = {}
        for _ in range(times or move.get("repeat", 1)):
            for step in move["steps"]:
                seconds, pose = step[0], step[1]
                t += seconds
                self._key(t, pose)
                if len(step) > 2 and step[2] > 0:
                    t += step[2]
                    self._key(t, pose)
                last = pose
        if move.get("stay"):
            self.current_pose = last
        else:
            t += 0.3
            self._key(t, {})
            self.current_pose = {}
        return t

    # ----------------------------------------------------------------- actions
    # Each action starts at the film's current time and moves the clock forward
    # (inside `with film.together():` each character keeps its own clock).

    def place(self, x, y, face=None):
        """Puts the character somewhere instantly (use at the start or on a cut)."""
        t = self.film._start(self)
        if t > 0:
            self._hold(t - 1 / self.film.fps)
        self.x, self.y = x, y
        if face is not None:
            self.angle = self._angle_to(face)
        self.current_pose = {}
        self._key(t, {})
        self._key_root(t)
        self.film._end(self, t)

    def face(self, target, seconds=0.35):
        """Turns the whole body toward a spot (x, y) or another character."""
        t = self.film._start(self)
        self._hold(t)
        self.angle = self._angle_to(target)
        t += seconds
        self._key_root(t)
        self._key(t, self.current_pose)
        self.film._end(self, t)

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
        pose["head"] = {"turn": max(-75, min(75, turn)), "nod": max(-40, min(40, nod))}
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

    def rest(self, seconds=0.4):
        self.pose({}, seconds)

    def play(self, move, times=None):
        """Plays a move from the library, e.g. "wave", "jump", "dance"."""
        t = self.film._start(self)
        self._key_root(t)
        self.film._end(self, self._play_from(t, move, times))

    def walk_to(self, x, y, speed=1.3, run=False):
        t = self.film._start(self)
        self._hold(t)
        target = Vector((x, y, 0))
        new_angle = self._angle_to(target)
        turn = abs(new_angle - self.angle)
        if turn > 0.05:
            self.angle = new_angle
            t += min(0.45, 0.15 + turn * 0.12)
            self._key_root(t, ("rotation_euler",))
            self._key(t, self.current_pose)

        distance = (target - self.position()).length
        if distance < 0.01:
            self.film._end(self, t)
            return
        step_len = 0.95 if run else 0.55
        steps = max(2, round(distance / step_len))
        duration = distance / speed
        step_t = duration / steps
        swing, arm, bob = (45, 50, 0.07) if run else (28, 24, 0.035)
        lean = 12 if run else 2
        bend = 80 if run else 15

        with self.film.linear_keys():
            self._key_root(t, ("location",))
        for i in range(steps):
            s = 1 if i % 2 == 0 else -1
            contact = {
                "leg_r": {"forward": swing * s}, "leg_l": {"forward": -swing * s},
                "arm_r": {"forward": -arm * s, "bend": bend}, "arm_l": {"forward": arm * s, "bend": bend},
                "body": {"lean": lean, "twist": 4 * s}, "head": {"nod": -lean * 0.5},
            }
            passing = {
                "arm_r": {"bend": bend}, "arm_l": {"bend": bend},
                "body": {"lean": lean, "bob": bob}, "head": {"nod": -lean * 0.5},
            }
            self._key(t + (i + 0.5) * step_t, contact)
            if i < steps - 1:
                self._key(t + (i + 1) * step_t, passing)
        t += duration
        self.x, self.y = x, y
        with self.film.linear_keys():
            self._key_root(t, ("location",))
        self.current_pose = {}
        t += 0.2
        self._key(t, {})
        self.film._end(self, t)

    def run_to(self, x, y):
        self.walk_to(x, y, speed=3.6, run=True)

    def say(self, text, seconds=None, gesture=None):
        """Says a line: subtitles + a talking mouth. gesture plays a move at the same time."""
        t = self.film._start(self)
        seconds = seconds or (1.0 + 0.06 * len(text))
        self.film._subtitle(t, t + seconds, self.name, text)

        rng = random.Random(f"{self.name}{text}")
        f = self.film.frame
        self.mouth.scale = (1, 1, 1)
        self.mouth.keyframe_insert("scale", frame=f(t))
        tt = t + 0.05
        while tt < t + seconds - 0.2:
            self.mouth.scale = (1 + rng.uniform(-0.15, 0.25), 1, rng.uniform(2.2, 3.6))
            self.mouth.keyframe_insert("scale", frame=f(tt))
            tt += rng.uniform(0.08, 0.13)
            self.mouth.scale = (1, 1, rng.uniform(0.7, 1.2))
            self.mouth.keyframe_insert("scale", frame=f(tt))
            tt += rng.uniform(0.07, 0.12)
        self.mouth.scale = (1, 1, 1)
        self.mouth.keyframe_insert("scale", frame=f(t + seconds))

        end = t + seconds
        if gesture:
            self._key_root(t)
            end = max(end, self._play_from(t, gesture))
        self.film._end(self, end)

    # ------------------------------------------------------------ automatic

    def _add_blinks(self, length):
        rng = random.Random(self.name)
        f = self.film.frame
        t = rng.uniform(0.5, 2.0)
        while t < length - 0.3:
            for dt, s in ((0.0, 1.0), (0.06, 0.1), (0.14, 1.0)):
                for eye in self.eyes:
                    eye.scale = (1, 1, s)
                    eye.keyframe_insert("scale", frame=f(t + dt))
            t += rng.uniform(2.2, 4.5)
