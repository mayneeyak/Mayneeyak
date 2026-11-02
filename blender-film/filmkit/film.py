"""The Film: clock, lighting, titles/subtitles/fades, and rendering to video."""

import math
import os
from contextlib import contextmanager

import bpy
from mathutils import Vector

from .camera import CameraRig
from .materials import color


def _clear_everything():
    for scene in list(bpy.data.scenes)[1:]:
        bpy.data.scenes.remove(scene)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.actions):
        for block in list(coll):
            coll.remove(block)


class Film:
    """Holds everything about one film. Time is in seconds from the start."""

    def __init__(self, title="My Film", fps=24, resolution=(1280, 720), font=None):
        _clear_everything()
        self.title_text = title
        self.font_path = font  # a .ttf/.otf file for titles and subtitles (default: Inter)
        self.fps = fps
        self.resolution = resolution
        self.scene = bpy.data.scenes[0]
        self.scene.name = "Film"
        self.scene.render.fps = fps
        self.collection = self.scene.collection
        self.characters = []

        self.t = 0.0
        self._clocks = None
        self._block_start = 0.0

        self._subtitles = []
        self._titles = []
        self._credits = []
        self._fade_keys = []
        self._fade_level = 0.0
        self._sounds = []

        self._setup_world()
        self.camera = CameraRig(self)

    # ------------------------------------------------------------------- clock

    def frame(self, seconds):
        return seconds * self.fps + 1

    def now(self):
        """The current time (inside `together()` this is when the block started)."""
        return self._block_start if self._clocks is not None else self.t

    def _start(self, who):
        if self._clocks is not None:
            return self._clocks.get(who, self._block_start)
        return self.t

    def _end(self, who, t):
        if self._clocks is not None:
            self._clocks[who] = t
        else:
            self.t = t

    @contextmanager
    def together(self):
        """Everything inside happens at the same time.
        Each character (or prop) still does its own actions one after another."""
        if self._clocks is not None:
            yield
            return
        self._block_start = self.t
        self._clocks = {}
        try:
            yield
        finally:
            self.t = max([self._block_start, *self._clocks.values()])
            self._clocks = None

    def wait(self, seconds):
        t = self._start("film")
        self._end("film", t + seconds)

    @contextmanager
    def _key_type(self, kind):
        prefs = bpy.context.preferences.edit
        old = prefs.keyframe_new_interpolation_type
        prefs.keyframe_new_interpolation_type = kind
        try:
            yield
        finally:
            prefs.keyframe_new_interpolation_type = old

    def linear_keys(self):
        return self._key_type("LINEAR")

    def constant_keys(self):
        return self._key_type("CONSTANT")

    # ------------------------------------------------------ world and lighting

    def _setup_world(self):
        world = bpy.data.worlds.get("Sky") or bpy.data.worlds.new("Sky")
        self.scene.world = world
        if world.node_tree is None:
            world.use_nodes = True
        self._background = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")

        sun_data = bpy.data.lights.new("Sun", "SUN")
        sun_data.angle = math.radians(8)
        self.sun = bpy.data.objects.new("Sun", sun_data)
        self.collection.objects.link(self.sun)
        self._apply_time(11.0)

    def _apply_time(self, hour):
        """Sets sun angle, sun color and sky color for a time of day (6 = sunrise, 18 = sunset)."""
        day = max(0.0, math.sin(math.pi * (hour - 6) / 12))  # 0 at sunrise/sunset, 1 at noon
        elevation = math.radians(4 + 56 * day)
        azimuth = math.radians(-60 + (hour - 6) * 10)
        self.sun.rotation_euler = (math.pi / 2 - elevation, 0, azimuth)
        warm = 1 - day
        noon_sun, low_sun = Vector((1.0, 0.96, 0.9)), Vector((1.0, 0.55, 0.28))
        self.sun.data.color = tuple(noon_sun.lerp(low_sun, warm ** 2))
        self.sun.data.energy = 1.5 + 2.5 * day
        noon_sky, low_sky = Vector(color("#a9cdff")), Vector(color("#ffc4a0"))
        sky = noon_sky.lerp(low_sky, warm ** 2)
        self._background.inputs["Color"].default_value = (*sky, 1)
        self._background.inputs["Strength"].default_value = 0.5 + 0.7 * day

    def _key_time(self, t):
        f = self.frame(t)
        self.sun.keyframe_insert("rotation_euler", frame=f)
        self.sun.data.keyframe_insert("color", frame=f)
        self.sun.data.keyframe_insert("energy", frame=f)
        self._background.inputs["Color"].keyframe_insert("default_value", frame=f)
        self._background.inputs["Strength"].keyframe_insert("default_value", frame=f)

    def time_of_day(self, hour, seconds=0.0):
        """Changes the light: 8 = morning, 12 = noon, 17.5 = golden hour, 18.3 = sunset.
        With seconds > 0 it changes slowly (doesn't move the clock)."""
        t = self.now()
        if seconds > 0:
            self._key_time(t)
        self._hour = hour
        self._apply_time(hour)
        self._key_time(t + seconds)

    # --------------------------------------------------------------- props

    def move(self, obj, to, seconds=1.0, style="smooth", spin=None, delay=0.0):
        """Moves a prop. style: "smooth", "linear" or "bounce" (drops and bounces).
        spin=(x, y, z) adds a rotation in degrees over the move (e.g. a rolling ball).
        delay waits that many seconds first. Moves of the same prop happen one after another."""
        t = self._start(obj) + delay
        f = self.frame
        start_loc = obj.location.copy()
        start_rot = obj.rotation_euler.copy()
        end_loc = Vector(to)
        obj.keyframe_insert("location", frame=f(t))
        obj.keyframe_insert("rotation_euler", frame=f(t))

        def rot_at(a):
            if spin is None:
                return start_rot
            return tuple(start_rot[i] + math.radians(spin[i]) * a for i in range(3))

        if style == "bounce":
            with self.linear_keys():
                steps = max(2, int(seconds * self.fps))
                for i in range(1, steps + 1):
                    a = i / steps
                    p = start_loc.lerp(end_loc, min(1.0, a * 1.4))
                    p.z = end_loc.z + (start_loc.z - end_loc.z) * _bounce_height(a)
                    obj.location = p
                    obj.rotation_euler = rot_at(a)
                    obj.keyframe_insert("location", frame=f(t + seconds * a))
                    obj.keyframe_insert("rotation_euler", frame=f(t + seconds * a))
        else:
            ctx = self.linear_keys() if style == "linear" else _nothing()
            with ctx:
                obj.keyframe_insert("location", frame=f(t))
                obj.location = end_loc
                obj.rotation_euler = rot_at(1.0)
                obj.keyframe_insert("location", frame=f(t + seconds))
                obj.keyframe_insert("rotation_euler", frame=f(t + seconds))
        self._end(obj, t + seconds)

    def wiggle(self, obj, degrees=6, seconds=0.8, delay=0.0):
        """Shakes a prop back and forth (doesn't move the clock)."""
        t = self.now() + delay
        base = obj.rotation_euler.copy()
        obj.keyframe_insert("rotation_euler", frame=self.frame(t))
        n = max(2, int(seconds / 0.1))
        for i in range(1, n + 1):
            k = 1 - i / n
            sign = 1 if i % 2 else -1
            obj.rotation_euler = (base.x + math.radians(degrees) * k * sign * 0.6, base.y + math.radians(degrees) * k * sign, base.z)
            obj.keyframe_insert("rotation_euler", frame=self.frame(t + i * seconds / n))
        obj.rotation_euler = base
        obj.keyframe_insert("rotation_euler", frame=self.frame(t + seconds))

    # --------------------------------------------------- titles and effects

    def black(self):
        """Screen goes black instantly."""
        t = self.now()
        if t > 0:
            self._fade_keys.append((t - 1 / self.fps, self._fade_level))
        self._fade_level = 1.0
        self._fade_keys.append((t, 1.0))

    def _fade_to(self, level, seconds, wait):
        t = self._start("film")
        self._fade_keys.append((t, self._fade_level))
        self._fade_level = level
        self._fade_keys.append((t + seconds, level))
        if wait:
            self._end("film", t + seconds)

    def fade_in(self, seconds=1.0, wait=False):
        """From black to the picture."""
        self._fade_to(0.0, seconds, wait)

    def fade_out(self, seconds=1.0, wait=True):
        """From the picture to black."""
        self._fade_to(1.0, seconds, wait)

    def title(self, text, small_text="", seconds=3.0):
        """A title card on black (waits until it's done)."""
        t = self._start("film")
        self._titles.append((t, t + seconds, text, small_text))
        self._end("film", t + seconds)

    def credits(self, lines, seconds=8.0):
        """Scrolling credits on black (waits until done)."""
        t = self._start("film")
        self._credits.append((t, t + seconds, list(lines)))
        self._end("film", t + seconds)

    def _subtitle(self, start, end, name, text):
        self._subtitles.append((start, end, f"{name}: {text}"))

    def music(self, path, volume=0.7, start=None):
        """Adds a sound or music file (mp3/wav/ogg) starting now (or at `start` seconds)."""
        self._sounds.append((self.now() if start is None else start, os.path.abspath(path), volume))

    # ----------------------------------------------------------------- finish

    def length(self):
        return self.t

    def finish(self):
        """Bakes the camera and builds the edit (titles, subtitles, fades). Call once at the end."""
        frame_end = int(math.ceil(self.t * self.fps)) + 1
        self.frame_end = frame_end
        self.scene.frame_start, self.scene.frame_end = 1, frame_end
        for char in self.characters:
            char._add_blinks(self.t)
        self.camera.bake(frame_end)
        self.scene.frame_set(1)
        self._build_edit(frame_end)
        try:
            bpy.context.window.scene = self.scene
        except (AttributeError, TypeError):
            pass

    def _load_font(self):
        path = self.font_path or os.path.join(bpy.utils.system_resource("DATAFILES"), "fonts", "Inter.woff2")
        try:
            return bpy.data.fonts.load(path, check_existing=True)
        except (RuntimeError, OSError):
            print(f"[filmkit] Couldn't load font {path}, using Blender's default")
            return None

    def _build_edit(self, frame_end):
        edit = bpy.data.scenes.get("Edit") or bpy.data.scenes.new("Edit")
        edit.render.fps = self.fps
        edit.frame_start, edit.frame_end = 1, frame_end
        ed = edit.sequence_editor_create()
        for strip in list(ed.strips):
            ed.strips.remove(strip)
        strips = ed.strips
        height = self.resolution[1]
        font = self._load_font()
        f = lambda s: int(round(self.frame(s)))  # noqa: E731

        film_strip = strips.new_scene("Film", self.scene, 1, 1)
        film_strip.frame_final_end = frame_end + 1

        def black_card(channel, start, end, name="Black"):
            card = strips.new_effect(name=name, type="COLOR", channel=channel, frame_start=f(start),
                                     length=max(1, f(end) - f(start)))
            card.color = (0, 0, 0)
            return card

        def text(channel, start, end, body, size, y, name="Text", fade=0.0):
            strip = strips.new_effect(name=name, type="TEXT", channel=channel, frame_start=f(start),
                                      length=max(1, f(end) - f(start)))
            strip.text = body
            strip.font_size = size
            strip.location = (0.5, y)
            strip.wrap_width = 0.9
            strip.color = (1, 1, 1, 1)
            strip.use_shadow = True
            if font is not None:
                strip.font = font
            for attr, value in (("anchor_x", "CENTER"), ("anchor_y", "CENTER"), ("alignment_x", "CENTER")):
                if hasattr(strip, attr):
                    setattr(strip, attr, value)
            if fade > 0:
                for t_key, a in ((start, 0), (start + fade, 1), (end - fade, 1), (end, 0)):
                    strip.blend_alpha = a
                    strip.keyframe_insert("blend_alpha", frame=self.frame(t_key))
            return strip

        if self._fade_keys:
            fader = black_card(2, 0, self.t + 1 / self.fps, "Fade")
            fader.frame_final_end = frame_end + 1
            fader.blend_alpha = 0.0
            fader.keyframe_insert("blend_alpha", frame=1)
            for t_key, level in sorted(self._fade_keys):
                fader.blend_alpha = level
                fader.keyframe_insert("blend_alpha", frame=self.frame(t_key))

        channel_end = {}
        for start, end, body in self._subtitles:
            channel = 3
            while channel_end.get(channel, -1) > start:
                channel += 1
            channel_end[channel] = end
            sub = text(channel, start, end, body, int(height * 0.045), 0.08, "Subtitle")
            if hasattr(sub, "use_box"):
                sub.use_box = True
                sub.box_color = (0, 0, 0, 0.45) if len(sub.box_color) == 4 else (0, 0, 0)

        for start, end, big, small in self._titles:
            black_card(8, start, end, "TitleCard")
            text(9, start, end, big, int(height * 0.11), 0.55, "Title", fade=min(0.6, (end - start) / 3))
            if small:
                text(10, start, end, small, int(height * 0.05), 0.4, "TitleSmall", fade=min(0.6, (end - start) / 3))

        for start, end, lines in self._credits:
            black_card(8, start, end, "CreditsCard")
            spacing = 0.08
            for i, line in enumerate(lines):
                if not line:
                    continue
                strip = text(9 + i, start, end, line, int(height * 0.05), 0, "Credit")
                y0 = -0.05 - i * spacing
                y1 = y0 + 1.15 + len(lines) * spacing
                with self.linear_keys():
                    strip.location = (0.5, y0)
                    strip.keyframe_insert("location", index=1, frame=self.frame(start))
                    strip.location = (0.5, y1)
                    strip.keyframe_insert("location", index=1, frame=self.frame(end))

        for i, (start, path, volume) in enumerate(self._sounds):
            if os.path.exists(path):
                sound = strips.new_sound(f"Sound{i}", path, 20 + i, f(start))
                sound.volume = volume
            else:
                print(f"[filmkit] Sound file not found, skipping: {path}")

        self.edit = edit

    # ------------------------------------------------------------------ render

    def _configure(self, quality, engine):
        final = quality == "final"
        width, height = self.resolution
        for scene in (self.scene, self.edit):
            scene.render.resolution_x, scene.render.resolution_y = width, height
            scene.render.resolution_percentage = 100 if final else 50
            scene.render.fps = self.fps

        film = self.scene
        if engine == "cycles":
            import addon_utils
            addon_utils.enable("cycles", default_set=True)
            film.render.engine = "CYCLES"
            film.cycles.device = "CPU"
            film.cycles.samples = 128 if final else 16
            film.cycles.use_adaptive_sampling = True
            film.cycles.max_bounces = 6 if final else 3
            film.cycles.use_denoising = True
            film.cycles.denoising_quality = "FAST" if not final else "HIGH"
            film.cycles.denoising_prefilter = "NONE" if not final else "ACCURATE"
            # Note: use_persistent_data is left off on purpose. It made animated objects
            # (the shaken tree top) render black partway through the film.
            film.render.use_persistent_data = False
        else:
            film.render.engine = "BLENDER_EEVEE"
            try:
                film.eevee.taa_render_samples = 64 if final else 16
            except AttributeError:
                pass
        transforms = [i.identifier for i in film.view_settings.bl_rna.properties["view_transform"].enum_items]
        film.view_settings.view_transform = "AgX" if "AgX" in transforms else "Filmic"
        self.edit.render.use_sequencer = True

    def snapshot(self, path, seconds, quality="preview", engine="eevee"):
        """Renders one moment of the film (with titles/subtitles) to a .png, to check a shot quickly."""
        self._configure(quality, engine)
        edit = self.edit
        settings = edit.render.image_settings
        if hasattr(settings, "media_type"):
            settings.media_type = "IMAGE"
        settings.file_format = "PNG"
        frame = int(round(self.frame(seconds)))
        edit.frame_start = edit.frame_end = frame
        base = os.path.splitext(os.path.abspath(path))[0]
        edit.render.filepath = base + "_"
        bpy.ops.render.render(animation=True, scene=edit.name)
        rendered = f"{base}_{frame:04d}.png"
        if os.path.exists(rendered):
            os.replace(rendered, base + ".png")

    def render(self, path, quality="preview", engine="eevee", frames=None):
        """Renders the finished film to an .mp4 file.

        quality: "preview" (half size, fast) or "final" (full size, clean)
        engine:  "eevee" (fast, needs a graphics card) or "cycles" (works anywhere, slower)
        frames:  (first, last) to render only part of the film
        """
        self._configure(quality, engine)
        edit = self.edit
        settings = edit.render.image_settings
        if hasattr(settings, "media_type"):
            settings.media_type = "VIDEO"
        settings.file_format = "FFMPEG"
        edit.render.ffmpeg.format = "MPEG4"
        edit.render.ffmpeg.codec = "H264"
        edit.render.ffmpeg.constant_rate_factor = "HIGH" if quality == "final" else "MEDIUM"
        if self._sounds:
            edit.render.ffmpeg.audio_codec = "AAC"
        if frames:
            edit.frame_start, edit.frame_end = frames
        else:
            edit.frame_start, edit.frame_end = 1, self.frame_end
        edit.render.filepath = os.path.abspath(path)
        print(f"[filmkit] Rendering {edit.frame_end - edit.frame_start + 1} frames with {engine} -> {path}")
        bpy.ops.render.render(animation=True, scene=edit.name)
        print(f"[filmkit] Done: {path}")


@contextmanager
def _nothing():
    yield


def _bounce_height(a):
    """Height (1 = start, 0 = ground) of something dropped, with two little bounces."""
    if a < 0.55:
        return 1 - (a / 0.55) ** 2
    if a < 0.8:
        u = (a - 0.55) / 0.25
        return 0.18 * (1 - (2 * u - 1) ** 2)
    if a < 0.95:
        u = (a - 0.8) / 0.15
        return 0.05 * (1 - (2 * u - 1) ** 2)
    return 0.0
