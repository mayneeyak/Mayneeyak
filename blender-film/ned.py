"""NED: The Jolly Rancher King of Maplewood Elementary

Ned is ten. Ned runs the candy business at Maplewood Elementary. Everybody buys from Ned:
the kids, his teacher... even the principal.

Run it:
  Preview in Blender:   open this file in the Scripting tab and press Run Script
  Render a video:       blender --background --python ned.py -- --render
  Full quality:         blender --background --python ned.py -- --render --quality final
  No graphics card:     add  --engine cycles
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
for _name in [m for m in sys.modules if m in ("filmkit", "school_sets") or m.startswith("filmkit.")]:
    del sys.modules[_name]  # pick up your latest edits when re-running inside Blender

from filmkit import Character, Film, command_line, props  # noqa: E402
from school_sets import classroom, hallway, playground, school_front  # noqa: E402

film = Film("NED", fps=24, resolution=(1280, 720))

# ------------------------------------------------------------------- SETS

props.ground(film, size=900)
front = school_front(film, (0, 0))
hall = hallway(film, (100, 0))
room = classroom(film, (200, 0))
yard = playground(film, (300, 0))
OFFSTAGE = (600, 600)

# ------------------------------------------------------------------- CAST

ned = Character(film, "Ned", build="kid", skin="#f3cfb3", shirt="#1d1d22", pants="#2d3550", shoes="#d93a3a",
                top="hoodie", hair="#6b4a2b", hair_style="buzz", cap="#c62828", cap_backwards=True,
                sunglasses=True, chain=True, face={"lids": 0.65, "smirk": 0.45, "smile": 0.2})
tyler = Character(film, "Tyler", build="kid", skin="#f1c7a3", shirt="#43a047", pants="#b9a37a", shoes="#1e5aa8",
                  hair="#c58a3a", hair_style="short", backpack="#e65100", eye_color="#3c6e9e")
maya = Character(film, "Maya", build="kid", skin="#8d5a3b", shirt="#ffb300", pants="#5e35b1", hair="#1a120c",
                 hair_style="ponytail", bottom="shorts", shoes="#f4f4f4", eye_color="#3b2412")
jaden = Character(film, "Jaden", build="kid", skin="#c68b62", shirt="#1e88e5", pants="#37474f", hair="#141010",
                  hair_style="short", glasses="#222222", top="hoodie", shoes="#ffffff", scale=0.92,
                  face={"brow_angle": 8, "smile": 0.1})
sofia = Character(film, "Sofia", build="kid", skin="#e9b994", shirt="#ec407a", pants="#455a64", hair="#4e2a12",
                  hair_style="long", bottom="skirt", shoes="#6d4c41", scale=0.97)
ben = Character(film, "Ben", build="kid", skin="#f5d0b5", shirt="#5c6bc0", pants="#263238", hair="#e0a96d",
                hair_style="short", cap="#1565c0", shoes="#212121", scale=1.03)
henderson = Character(film, "Mrs. Henderson", build="adult", skin="#f0c8a8", shirt="#6d8f5e", pants="#4a3b5c",
                      top="cardigan", bottom="skirt", hair="#8a5a3c", hair_style="bun", glasses="#7a2e2e",
                      shoes="#3b2a20", sole="#2a1e18")
dawson = Character(film, "Principal Dawson", build="adult", skin="#d7a17e", shirt="#2e3440", pants="#2e3440",
                   top="suit", hair="#5a5a5a", hair_style="bald", mustache=True, tie="#b71c1c", shoes="#111111",
                   sole="#222222", width=1.2, face={"smile": 0.0, "brow_angle": -6})
everyone = [ned, tyler, maya, jaden, sofia, ben, henderson, dawson]

# Candy and cash (hidden until someone is holding them)
watermelon = props.candy(film, "watermelon")
grape = props.candy(film, "grape")
blue = props.candy(film, "blue raspberry")
cherry = props.candy(film, "cherry")
montage_candy = [props.candy(film, f) for f in ("green apple", "cherry", "watermelon")]
bills = [props.cash(film) for _ in range(8)]
for thing in [watermelon, grape, blue, cherry, *montage_candy, *bills]:
    film.hide(thing)


def offstage(*people):
    for i, person in enumerate(people):
        person.place(OFFSTAGE[0] + i * 2, OFFSTAGE[1])


def sale(buyer, money, candy):
    """The deal: buyer hands over cash, Ned pockets it and hands over the candy."""
    buyer.give(money, ned)
    ned.pocket(money)
    ned.give(candy, buyer)


# ============================================================== SCENE 1: FRONT

film.time_of_day(8.6)
offstage(*everyone)
ned.place(-6.2, -1.0, face=(-1.2, 2.2))
tyler.place(1.6, 3.2, face=(4, 2.5))
maya.place(2.6, 3.0, face=(1.6, 3.2))
ben.place(5.8, 4.1, face=(6.6, 3.5))
sofia.place(6.6, 3.6, face=(5.8, 4.1))

film.title("NED", "The Jolly Rancher King of Maplewood Elementary", seconds=3.5)
film.black()
film.camera.wide((0, 5, 2.2), distance=19, height=5, angle=-18, lens=30)
film.camera.wide((0, 4, 1.6), distance=14, height=3, angle=-8, lens=30, duration=4)
film.fade_in(1.2)
film.caption("Maplewood Elementary. 7:58 AM.", seconds=2.8)
film.wait(2.0)

with film.together():
    ned.walk_to(-1.2, 2.2, style="swagger")
    film.camera.follow(ned, offset=(1.6, -2.6, 0.45), lens=24)
    film.camera.two_shot(tyler, maya, delay=2.4)
    tyler.wait(2.2)
    tyler.face(maya)
    tyler.say("Yo... that's Ned.")
    maya.wait(2.6)
    maya.look_at(ned)
    maya.wait(1.3)
    maya.say("I heard he made four hundred dollars last week.", gesture="talk")
    film.camera.hero(ned, angle=30, delay=7.2)

with film.together():
    ned.face(maya)
    tyler.face(ned)
    maya.face(ned)
film.camera.close_up(ned, angle=-12)
film.wait(0.3)
ned.set_face(glasses=1.0, brow_raise=0.03, seconds=0.6)
ned.say("Four-fifty.")
ned.set_face(glasses=0.0, brow_raise=0.0, seconds=0.5)
film.camera.two_shot(tyler, maya)
with film.together():
    tyler.play("gasp")
    maya.play("surprised")
film.camera.wide((-0.5, 3.5, 1.5), distance=9, height=1.6, angle=-25, lens=30)
with film.together():
    ned.walk_to(-0.4, 4.4, style="swagger")
    film.fade_out(0.8, delay=2.2)

# ============================================================== SCENE 2: HALLWAY

offstage(*everyone)
hx = 100
ned.place(hx, 0.8, face=(hx, 3))
for kid, spot in zip([tyler, jaden, sofia, ben], hall["line"]):
    kid.place(spot[0], spot[1], face=(hx, 0.8))
film.camera.wide((hx + 1.5, 1.0, 1.0), distance=6.5, height=0.6, angle=-12, lens=30)
film.fade_in(0.8)
film.caption("Locker 4B.", seconds=2.5)
film.wait(0.6)
with film.together():
    ned.play("point")
    film.move(hall["door_hinge"], tuple(hall["door_hinge"].location), seconds=0.8, spin=(0, 0, -115), delay=0.35)
film.camera.move((hx - 0.25, -0.4, 1.25), (hx, 1.6, 1.05), duration=1.6, lens=35)
film.wait(1.8)
film.caption("Ned's office.", seconds=2.0)
film.wait(1.0)

film.camera.two_shot(ned, tyler, side=-1)
with film.together():
    tyler.walk_to(hx + 0.75, 0.55)
    ned.face((hx + 0.75, 0.55))
tyler.face(ned)
tyler.say("Ned. I need a watermelon. Bad.", gesture="shrug")
film.camera.close_up(ned, angle=-20)
ned.say("Two bucks.", gesture="cool_nod")
film.camera.two_shot(ned, tyler, side=-1)
sale(tyler, bills[0], watermelon)
tyler.say("Pleasure doing business.", gesture="cool_nod")

with film.together():
    tyler.walk_to(hx - 2.6, -0.4)
    jaden.walk_to(hx + 0.75, 0.55)
    film.camera.two_shot(ned, jaden, side=-1, delay=0.5)
jaden.face(ned)
jaden.say("Do you have... grape?", gesture="shrug")
film.camera.close_up(ned, angle=-20)
ned.set_face(smirk=0.85, seconds=0.3)
ned.say("Grape's premium. Three bucks.")
film.camera.close_up(jaden, angle=15)
jaden.say("That's my whole lunch money!", gesture="gasp")
film.camera.close_up(ned, angle=-20)
ned.say("Then lunch is a Jolly Rancher.", gesture="shrug")
film.camera.two_shot(ned, jaden, side=-1)
sale(jaden, bills[1], grape)
jaden.play("sad")
film.fade_out(0.8)

# ============================================================ SCENE 3: CLASSROOM

offstage(*everyone)
rx = 200
seats = room["seats"]
seated = [(ned, seats[(2, 2)]), (tyler, seats[(1, 1)]), (maya, seats[(1, 0)]), (jaden, seats[(0, 2)]),
          (sofia, seats[(0, 0)]), (ben, seats[(2, 0)])]
for kid, (sx, sy) in seated:
    kid.place(sx, sy, face=(sx, sy + 5))
henderson.place(rx, 3.1, face=(rx, -3))
with film.together():
    for kid, _ in seated:
        kid.sit(0.345, seconds=0.01)
film.camera.wide((rx + 0.5, 0.2, 0.9), distance=4.0, height=1.6, angle=200, lens=26)
film.fade_in(0.8)
film.caption("Room 4B. Second period.", seconds=2.5)
henderson.say("Okay class, open your books to page forty-two.", gesture="talk")
film.camera.medium(ned, angle=8)
ned.play("lean_back")
film.wait(0.8)
film.camera.close_up(henderson, angle=10)
henderson.say("Ned.")
henderson.wait(0.5)
henderson.say("See me after class.", gesture="point")
film.camera.wide((rx + 0.5, -0.5, 0.8), distance=4.2, height=1.2, angle=190, lens=26)
with film.together():
    tyler.look_at(ned)
    maya.look_at(ned)
    jaden.look_at(ned)
    tyler.say("Ooooooooh.", seconds=1.6)
film.camera.close_up(ned, angle=0)
ned.set_face(glasses=1.0, brow_raise=0.03, seconds=0.7)
film.wait(1.2)
film.fade_out(0.7)

# After class: just the two of them
offstage(*[k for k, _ in seated if k is not ned])
ned.stand(seconds=0.01)
ned.set_face(glasses=0.0, brow_raise=0.0, smirk=0.45, seconds=0.01)
ned.place(rx - 1.6, 1.25, face=(rx - 1.6, 3))
henderson.place(rx - 1.6, 2.15, face=(rx - 1.6, 0))
film.camera.two_shot(henderson, ned)
film.fade_in(0.7)
film.caption("After class...", seconds=2.2)
film.wait(1.2)
henderson.play("sneaky_look")
film.camera.close_up(henderson, angle=-15)
henderson.say("...Do you have any blue raspberry?", gesture="whisper")
film.camera.close_up(ned, angle=40)
ned.set_face(smirk=0.9, seconds=0.3)
ned.say("For you, Mrs. H? Five bucks.")
film.camera.close_up(henderson, angle=-15)
henderson.say("FIVE?!", seconds=1.3, gesture="gasp")
film.camera.close_up(ned, angle=40)
ned.say("Teacher price.", gesture="cool_nod")
film.camera.two_shot(henderson, ned)
henderson.play("sigh")
sale(henderson, bills[2], blue)
henderson.say("This stays between us.", gesture="nod")
henderson.pocket(blue)
film.fade_out(0.8)

# ============================================================ SCENE 4: PLAYGROUND

offstage(*everyone)
film.time_of_day(12.5)
yx, oy = yard["office"][0], yard["office"][1]
ned.place(yx, oy, face=(yx, -5))
ned.set_face(smirk=0.5, seconds=0.01)
ned.sit(0.34, seconds=0.01)
buyers = [sofia, ben, maya]
for kid, spot in zip(buyers + [tyler, jaden], yard["line"]):
    kid.place(spot[0], spot[1], face=(yx, oy))
customer_spot = (yx, oy - 0.62)
film.camera.wide((yx + 1.8, 1.6, 0.9), distance=8, height=1.4, angle=-15, lens=30)
film.fade_in(0.8)
film.caption("Recess.", seconds=2.0)
film.wait(1.5)
film.caption("Business was booming.", seconds=3.0)
pile = yard["pile"]
for i, kid in enumerate(buyers):
    kid.walk_to(*customer_spot)
    kid.face(ned)
    if i == 0:
        film.camera.two_shot(ned, kid, side=-1)
    sale(kid, bills[3 + i], montage_candy[i])
    film.grow(pile, 0.6 + 0.25 * (i + 1), seconds=0.4)
    with film.together():
        kid.walk_to(yx - 2.6 - i * 0.4, -0.9)
        if i < len(buyers) - 1:
            buyers[i + 1].walk_to(customer_spot[0] + 0.9, customer_spot[1] + 0.1)
offstage(*buyers)

# The principal
dawson.place(yx + 4.2, -1.6, face=(yx, oy))
film.camera.two_shot(tyler, jaden, side=-1)
with film.together():
    tyler.look_at(dawson)
    jaden.look_at(dawson)
    jaden.say("It's Principal Dawson!", gesture="gasp")
with film.together():
    tyler.run_to(yx + 10, 6)
    jaden.run_to(yx + 11, 5)
    film.camera.follow(dawson, offset=(-2.2, -3.6, 1.0), lens=30)
    dawson.walk_to(customer_spot[0] + 0.15, customer_spot[1] - 0.15)
offstage(tyler, jaden)
dawson.face(ned)
film.camera.hero(ned, angle=-25)
ned.play("lean_back")
film.camera.close_up(dawson, angle=20)
dawson.play("arms_crossed")
dawson.say("Mr. Ned. We need to talk.")
film.camera.close_up(ned, angle=-45)
ned.set_face(glasses=1.0, seconds=0.6)
ned.say("...Talk.")
film.camera.close_up(dawson, angle=20)
dawson.play("sneaky_look")
dawson.say("Two cherries. And keep it quiet.", gesture="whisper")
film.camera.close_up(ned, angle=-45)
ned.set_face(glasses=0.0, seconds=0.4)
ned.say("I don't know you. You don't know me.", gesture="cool_nod")
film.camera.two_shot(ned, dawson, side=-1)
ned.rest()
dawson.give(bills[6], ned)
ned.pocket(bills[6])
ned.give(cherry, dawson)
film.grow(pile, 1.6, seconds=0.4)
dawson.pocket(cherry)

# ================================================================ ENDING

film.time_of_day(17.7, seconds=4)
film.camera.orbit((yx + 0.2, oy, 0.6), radius=2.6, height=0.35, duration=9, start=-40, end=40, lens=32)
with film.together():
    dawson.walk_to(yx - 5, -2.5)
    ned.play("count_money")
ned.say("Business...", seconds=1.4)
ned.wait(0.4)
ned.say("...is sweet.", gesture="cool_nod")
film.wait(1.0)
film.fade_out(2.0)
film.title("NED WILL RETURN", "in  THE SOUR PATCH WARS", seconds=3.0)
film.credits([
    "NED",
    "The Jolly Rancher King of Maplewood Elementary",
    "",
    "Ned ............ himself",
    "Tyler, Maya, Jaden, Sofia, Ben ............ customers",
    "Mrs. Henderson ............ blue raspberry fan",
    "Principal Dawson ............ two cherries",
    "",
    "No teachers were harmed",
    "in the making of this film.",
    "",
    "Made entirely with Python + Blender",
], seconds=8)

# ------------------------------------------------------------------ OUTPUT

film.finish()
print(f"[ned] Film length: {film.length():.1f} seconds")

opts = command_line()
if opts["render"]:
    out = opts["out"] or os.path.join(HERE, "renders", f"ned_{opts['quality']}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    film.render(out, quality=opts["quality"], engine=opts["engine"], frames=opts["frames"])
