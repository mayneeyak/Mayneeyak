"""filmkit: make 3D animated films with Python in Blender.

    from filmkit import Film, Character, props

    film = Film("My Film")
    props.ground(film)
    sam = Character(film, "Sam", shirt="#ff7043")
    sam.place(0, 0)
    film.camera.medium(sam)
    sam.say("Hello, world!", gesture="wave")
    film.finish()
    film.render("my_film.mp4")
"""

import sys

import bpy  # noqa: F401  (must come first: it makes mathutils and bmesh available)

from . import props
from .character import Character
from .film import Film
from .moves import MOVES

__all__ = ["Film", "Character", "props", "MOVES", "command_line"]


def command_line():
    """Options passed after the script name, e.g.
        blender --background --python my_film.py -- --render --quality final
    Returns a dict like {"render": True, "quality": "final", "engine": "eevee", "out": None}."""
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
    elif sys.argv and sys.argv[0].endswith(".py"):
        args = sys.argv[1:]
    else:
        args = []
    opts = {"render": False, "quality": "preview", "engine": "eevee", "out": None, "frames": None}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--render":
            opts["render"] = True
        elif a in ("--quality", "--engine", "--out") and i + 1 < len(args):
            opts[a[2:]] = args[i + 1]
            i += 1
        elif a == "--frames" and i + 2 < len(args):
            opts["frames"] = (int(args[i + 1]), int(args[i + 2]))
            i += 2
        i += 1
    return opts
