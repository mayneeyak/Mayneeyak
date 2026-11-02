"""PARK PALS - Episode 1: The Missing Ball

A short 3D animated film written entirely in Python with filmkit + Blender.

Run it:
  Preview in Blender:   open this file in Blender's Scripting tab and press Run Script,
                        then press Space in the 3D viewport to watch the animation.
  Render a video:       blender --background --python park_pals.py -- --render
  Full quality:         blender --background --python park_pals.py -- --render --quality final
  No graphics card:     add  --engine cycles

Coordinates are in meters. The camera usually looks from the front (-Y) toward the
houses at the back (+Y). x goes left (-) to right (+).
"""

import os
import sys

# Let Python find the filmkit folder next to this file (also when run from Blender's text editor).
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
    del sys.modules[_name]  # pick up your latest edits when re-running inside Blender

from filmkit import Character, Film, command_line, props  # noqa: E402

film = Film("Park Pals", fps=24, resolution=(1280, 720))

# ------------------------------------------------------------------- THE SET

props.ground(film, size=90)
props.path(film, (-40, -4), (40, -4), width=2.2)
tree_top = props.tree(film, 5, 3)
props.tree(film, -12, 9, height=2.8, leaves="#5aa843")
props.tree(film, 16, 11, height=3.6, leaves="#468f36")
props.bush(film, -7, 4)
props.bush(film, 10, 1.5, size=0.7)
props.bench(film, -5, 3.2)
props.lamp(film, -9, -2.6)
props.lamp(film, 13, -2.6)
props.house(film, -8, 20, walls="#f0dcc0", roof="#b94a3c")
props.house(film, 7, 22, walls="#cfe3f0", roof="#3c5aa0")
props.fence(film, (-40, 27), (40, 27))
props.flowers(film, -3, -7, count=26, radius=1.4)
props.flowers(film, 8, -7.5, count=18, radius=1.1)
props.rock(film, 12, -1, size=0.4)

BALL_IN_TREE = (4.2, 1.15, 4.3)
ball = props.ball(film, *BALL_IN_TREE)

# ------------------------------------------------------------------- THE CAST

max_ = Character(film, "Max", shirt="#e04646", pants="#2d4a8a", hair="#5a3a1e")
lily = Character(film, "Lily", skin="#efbf98", shirt="#ff9ec4", pants="#5b4aa8",
                 hair="#f2cd5c", long_hair=True)

# --------------------------------------------------------------- SCREENPLAY

film.time_of_day(10)
max_.place(-16, -4, face=(0, -4))
lily.place(16, -4, face=(0, -4))

film.title("PARK PALS", "Episode 1: The Missing Ball", seconds=3.5)

# Scene 1 - a sunny morning in the park
film.black()
film.camera.orbit((0, 3, 1), radius=19, height=6, duration=6, start=-45, end=5, lens=28)
film.fade_in(1.5)
film.wait(3.5)

film.camera.follow(max_, offset=(2.5, -7, 2), lens=35)
max_.walk_to(-2, -1)
max_.face((0, -6))
film.camera.close_up(max_)
max_.play("look_around")
max_.say("Has anyone seen my red ball?", gesture="sad")

# Lily arrives
film.camera.wide((0, -1, 1), distance=11, height=2.5, angle=10, lens=32)
lily.walk_to(1.5, -1)
with film.together():
    lily.face(max_)
    max_.face(lily)
film.camera.two_shot(max_, lily)
lily.say("Hi Max! Why do you look so sad?", gesture="wave")
film.camera.over_shoulder(lily, max_)
max_.say("I lost my ball. I've looked everywhere!", gesture="shrug")
film.camera.over_shoulder(max_, lily)
lily.say("Don't worry. Let's look together!", gesture="nod")

# Scene 2 - the search
film.camera.wide((0, 1, 1), distance=15, height=5, angle=-15, lens=30)
film.camera.wide((0, 1, 1), distance=12, height=3.5, angle=8, lens=30, duration=5)
with film.together():
    max_.walk_to(-4, 1.8)
    max_.play("look_around")
    lily.walk_to(2.2, 0.2)
    lily.play("look_around")

film.camera.medium(lily, angle=25)
lily.look_at(BALL_IN_TREE)
lily.play("surprised")
film.camera.move((1.2, -2.5, 1.7), BALL_IN_TREE, duration=1.5, lens=45)
lily.say("Look! It's stuck up in the tree!", gesture="point_up")

# Max tries to reach it
film.camera.wide((3.5, 1, 1.8), distance=8, height=1.5, angle=-10, lens=32)
max_.run_to(3.4, -0.2)
max_.face((4.2, 1.15))
max_.play("jump")
max_.play("jump")
film.camera.close_up(max_, angle=-20)
max_.say("I can't reach it!", gesture="sad")
film.camera.close_up(lily, angle=20)
lily.play("think")
lily.say("Hmm... I have an idea!", gesture="point_up")

# Scene 3 - the kick
film.camera.follow(lily, offset=(5, -3.5, 1.8), lens=35)
lily.walk_to(5, 1.9)
lily.face((5, 3))
film.camera.wide((4.5, 2, 2), distance=9, height=1.8, angle=35, lens=30)
with film.together():
    lily.play("kick")                                   # the foot hits the tree at ~0.42s
    film.camera.shake(0.08, 0.6, delay=0.42)
    film.wiggle(tree_top, degrees=7, seconds=0.9, delay=0.42)
    film.move(ball, (4.2, 1.15, 0.22), seconds=1.3, style="bounce", delay=0.6)
    film.move(ball, (3.5, 0.45, 0.22), seconds=0.7)    # then it rolls to Max

# The happy ending
film.camera.close_up(max_, angle=-15)
max_.play("surprised")
max_.say("My ball! You did it, Lily!", gesture="cheer")
lily.face(max_)
film.camera.two_shot(max_, lily)
lily.say("That's what friends are for!", gesture="wave")

film.time_of_day(17.6, seconds=6)
middle = ((max_.x + lily.x) / 2, (max_.y + lily.y) / 2, 1.0)
film.camera.orbit(middle, radius=6, height=1.6, duration=7, start=-20, end=70, lens=32)
with film.together():
    max_.play("dance")
    lily.play("dance")
with film.together():
    max_.play("bow")
    lily.play("bow")

film.fade_out(2)
film.title("THE END", seconds=2.5)
film.credits([
    "PARK PALS",
    "",
    "Starring",
    "Max",
    "Lily",
    "and the Red Ball",
    "",
    "Made entirely with Python",
    "",
    "Thanks for watching!",
], seconds=9)

# ------------------------------------------------------------------ OUTPUT

film.finish()
print(f"[park_pals] Film length: {film.length():.1f} seconds")

opts = command_line()
if opts["render"]:
    out = opts["out"] or os.path.join(HERE, "renders", f"park_pals_{opts['quality']}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    film.render(out, quality=opts["quality"], engine=opts["engine"], frames=opts["frames"])
