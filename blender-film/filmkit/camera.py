"""The film camera: shots, cuts, moves, orbits, follow-cams and shake.

Camera calls never move the film clock forward: they start at the current time
(plus an optional `delay`) and the screenplay carries on. duration=0 is a hard cut.
"""

import math
import random

import bpy
from mathutils import Vector


def _v(p):
    p = tuple(p)
    return Vector(p if len(p) == 3 else (p[0], p[1], 0.0))


def _smooth(a):
    a = max(0.0, min(1.0, a))
    return a * a * (3 - 2 * a)


class CameraRig:
    def __init__(self, film):
        self.film = film
        data = bpy.data.cameras.new("FilmCamera")
        data.lens = 35
        data.clip_start = 0.05
        data.clip_end = 1000
        data.dof.use_dof = True
        data.dof.aperture_fstop = 5.6
        self.obj = bpy.data.objects.new("FilmCamera", data)
        self.obj.rotation_mode = "QUATERNION"
        film.collection.objects.link(self.obj)
        film.scene.camera = self.obj
        self.events = []
        self.depth_of_field = True

    def _add(self, kind, delay, **kw):
        self.events.append(dict(kind=kind, t=self.film.now() + delay, order=len(self.events), **kw))

    # ------------------------------------------------------------ basic moves

    def cut(self, position, look_at, lens=35, delay=0.0):
        """Jumps straight to a new camera position."""
        self._add("cut", delay, pos=_v(position), target=_v(look_at), lens=lens)

    def move(self, position, look_at, duration=2.0, lens=None, delay=0.0):
        """Glides smoothly from wherever the camera is to a new position."""
        self._add("move", delay, pos=_v(position), target=_v(look_at), lens=lens, duration=duration)

    def orbit(self, center, radius=8.0, height=3.0, duration=6.0, start=0.0, end=90.0, lens=35, delay=0.0):
        """Circles around a point. Angle 0 is in front (the -Y side), 90 is to the right."""
        self._add("orbit", delay, center=_v(center), radius=radius, height=height,
                  duration=duration, start=start, end=end, lens=lens)

    def follow(self, character, offset=(2, -7, 2.2), duration=4.0, lens=35, delay=0.0):
        """Tracks a character from a fixed offset until the next camera call."""
        self._add("follow", delay, char=character, offset=_v(offset), duration=duration, lens=lens)

    def shake(self, strength=0.08, duration=0.5, delay=0.0):
        """Adds a quick shake on top of the current shot (bumps, crashes, kicks)."""
        self._add("shake", delay, strength=strength, duration=duration)

    # --------------------------------------------------------------- shot types

    def _shot(self, pos, target, lens, duration, delay):
        if duration and duration > 0:
            self.move(pos, target, duration, lens, delay)
        else:
            self.cut(pos, target, lens, delay)

    @staticmethod
    def _rotate(vec, degrees):
        a = math.radians(degrees)
        return Vector((vec.x * math.cos(a) - vec.y * math.sin(a), vec.x * math.sin(a) + vec.y * math.cos(a), vec.z))

    def close_up(self, char, angle=0, distance=2.3, lens=45, duration=0, delay=0.0):
        """Face fills the frame. angle swings the camera around the character (degrees)."""
        head = char.head_position()
        d = self._rotate(char.forward(), angle)
        self._shot(head + d * distance + Vector((0, 0, 0.05)), head, lens, duration, delay)

    def medium(self, char, angle=0, distance=3.4, lens=40, duration=0, delay=0.0):
        """Waist up."""
        chest = char.position() + Vector((0, 0, 1.05 * char.scale))
        d = self._rotate(char.forward(), angle)
        self._shot(chest + d * distance + Vector((0, 0, 0.2)), chest, lens, duration, delay)

    def two_shot(self, a, b, side=None, lens=35, duration=0, delay=0.0):
        """Both characters side by side in frame."""
        pa, pb = a.position(), b.position()
        mid = (pa + pb) / 2
        diff = pb - pa
        direction = diff.normalized() if diff.length > 1e-3 else Vector((1, 0, 0))
        perp = Vector((-direction.y, direction.x, 0))
        if side is not None:
            perp *= side
        elif perp.y > 0:
            perp = -perp  # default: film from the front (-Y) side
        distance = max(3.6, diff.length * 1.5)
        self._shot(mid + perp * distance + Vector((0, 0, 1.35)), mid + Vector((0, 0, 1.1)), lens, duration, delay)

    def over_shoulder(self, from_char, to_char, lens=45, duration=0, delay=0.0):
        """Behind one character's shoulder, looking at the other."""
        pf = from_char.position()
        d = (to_char.position() - pf).normalized()
        right = Vector((-d.y, d.x, 0)) * -1
        pos = pf - d * 1.7 + right * 0.7 + Vector((0, 0, 1.55 * from_char.scale))
        self._shot(pos, to_char.head_position(), lens, duration, delay)

    def wide(self, center, distance=14, height=4, angle=0, lens=30, duration=0, delay=0.0):
        """Shows the whole scene. angle swings around the center (0 = from the front)."""
        c = _v(center)
        offset = self._rotate(Vector((0, -distance, 0)), angle)
        self._shot(c + offset + Vector((0, 0, height)), c, lens, duration, delay)

    # -------------------------------------------------------------------- bake

    def bake(self, frame_end):
        """Turns all camera events into one keyframe per frame."""
        scene, fps = self.film.scene, self.film.fps
        events = sorted((e for e in self.events if e["kind"] != "shake"), key=lambda e: (e["t"], e["order"]))
        shakes = [e for e in self.events if e["kind"] == "shake"]
        needs_frame_set = any(e["kind"] == "follow" for e in events)
        if not events:
            events = [dict(kind="cut", t=0, pos=Vector((0, -12, 3)), target=Vector((0, 0, 1)), lens=35)]

        state = None
        idx = -1
        current = events[0]
        rng = random.Random(7)
        cam = self.obj
        with self.film.constant_keys():
            for frame in range(1, frame_end + 1):
                t = (frame - 1) / fps
                while idx + 1 < len(events) and events[idx + 1]["t"] <= t + 1e-6:
                    idx += 1
                    current = events[idx]
                    current["from"] = state
                if needs_frame_set:
                    scene.frame_set(frame)
                state = self._evaluate(current, t, state)
                pos, target, lens = state

                for s in shakes:
                    if s["t"] <= t < s["t"] + s["duration"]:
                        k = s["strength"] * (1 - (t - s["t"]) / s["duration"])
                        jitter = Vector((rng.uniform(-k, k), rng.uniform(-k, k), rng.uniform(-k, k)))
                        pos, target = pos + jitter, target + jitter * 0.5

                cam.location = pos
                cam.rotation_quaternion = (target - pos).to_track_quat("-Z", "Y")
                cam.data.lens = lens
                cam.data.dof.use_dof = self.depth_of_field
                cam.data.dof.focus_distance = max(0.1, (target - pos).length)
                cam.keyframe_insert("location", frame=frame)
                cam.keyframe_insert("rotation_quaternion", frame=frame)
                cam.data.keyframe_insert("lens", frame=frame)
                cam.data.dof.keyframe_insert("focus_distance", frame=frame)

    @staticmethod
    def _evaluate(e, t, prev):
        kind = e["kind"]
        if kind == "cut":
            return e["pos"], e["target"], e["lens"]
        if kind == "move":
            start = e.get("from") or (e["pos"], e["target"], e["lens"] or 35)
            a = _smooth((t - e["t"]) / max(e["duration"], 1e-6))
            end_lens = e["lens"] if e["lens"] else start[2]
            return (start[0].lerp(e["pos"], a), start[1].lerp(e["target"], a),
                    start[2] + (end_lens - start[2]) * a)
        if kind == "orbit":
            a = max(0.0, min(1.0, (t - e["t"]) / max(e["duration"], 1e-6)))
            ang = math.radians(e["start"] + (e["end"] - e["start"]) * a)
            c = e["center"]
            pos = c + Vector((math.sin(ang) * e["radius"], -math.cos(ang) * e["radius"], e["height"]))
            return pos, c.copy(), e["lens"]
        if kind == "follow":
            p = e["char"].root.matrix_world.translation.copy()
            p.z = 0
            look = p + Vector((0, 0, 1.0 * e["char"].scale))
            return p + e["offset"], look, e["lens"]
        return prev
