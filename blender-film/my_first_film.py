"""A tiny starter film. Copy this file to begin your own!

Run it the same way as park_pals.py:
  blender --background --python my_first_film.py -- --render
"""

import os
import sys

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.getcwd()
if not os.path.isdir(os.path.join(HERE, "filmkit")):
    import bpy
    for _text in bpy.data.texts:
        if _text.filepath:
            HERE = os.path.dirname(bpy.path.abspath(_text.filepath))
            break
sys.path.insert(0, HERE)
for _name in [m for m in sys.modules if m == "filmkit" or m.startswith("filmkit.")]:
    del sys.modules[_name]

from filmkit import Character, Film, command_line, props  # noqa: E402

film = Film("My First Film")

# 1. Build a set
props.ground(film)
props.tree(film, 3, 4)
props.flowers(film, -2, 1, count=15)

# 2. Make a character
sam = Character(film, "Sam", shirt="#ff7043", pants="#37474f", hair="#212121")
sam.place(-6, 0, face=(0, 0))

# 3. Write the story
film.title("My First Film", "starring Sam", seconds=2.5)
film.camera.wide((0, 0, 1), distance=10, height=2.5)
sam.walk_to(0, 0)
sam.face((0, -5))                       # turn toward the camera
film.camera.medium(sam, duration=1.5)   # smooth camera move closer
sam.say("Hello! I was made with Python.", gesture="wave")
sam.play("jump")
film.camera.close_up(sam)
sam.say("Watch this!")
film.camera.wide((0, 0, 1), distance=8, height=2)
sam.play("dance")
sam.play("bow")
film.fade_out(1.5)

# 4. Finish (and render if asked)
film.finish()
opts = command_line()
if opts["render"]:
    out = opts["out"] or os.path.join(HERE, "renders", "my_first_film.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    film.render(out, quality=opts["quality"], engine=opts["engine"], frames=opts["frames"])
