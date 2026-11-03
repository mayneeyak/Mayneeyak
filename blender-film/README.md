# filmkit: 3D animated films with Python

Write a film like a screenplay in Python, and Blender turns it into a rendered 3D video:

```python
film.camera.close_up(max_)
max_.say("Has anyone seen my red ball?", gesture="sad")
lily.walk_to(1.5, -1)
film.camera.two_shot(max_, lily)
lily.say("Hi Max! Why do you look so sad?", gesture="wave")
```

Included:

| File | What it is |
|---|---|
| `ned.py` | **NED: The Jolly Rancher King of Maplewood Elementary**: a ~3 minute film, 8 characters, 4 sets |
| `school_sets.py` | The school sets used by NED: school front, hallway with lockers, classroom, playground |
| `park_pals.py` | **Park Pals, Episode 1**: a ~1.5 minute example film (two characters, 3 scenes, titles, credits) |
| `my_first_film.py` | A tiny starter film to copy for your own |
| `filmkit/` | The engine (characters, moves, camera, sets, titles, rendering) |

## What you need

- **[Blender](https://www.blender.org/download/)**, free 3D software (Windows, Mac or Linux; tested with Blender 5.0).
  It needs a computer: it doesn't run on phones or tablets.
- That's it. Blender has Python built in.

## Running a film

**Option A: inside Blender (best for writing and previewing)**
1. Open Blender, go to the **Scripting** tab, click **Open** and pick `park_pals.py`.
2. Press **Run Script** (▶). The set, characters and animation are built.
3. Go back to the **Layout** tab, hover over the 3D view, press **Numpad 0** to look through the film camera
   and **Space** to play it in real time.
4. Edit the script and press Run Script again; it rebuilds everything from scratch.

**Option B: render a video from the command line**
```bash
blender --background --python park_pals.py -- --render                      # quick preview (640x360)
blender --background --python park_pals.py -- --render --quality final      # full HD
blender --background --python park_pals.py -- --render --engine cycles      # if EEVEE fails (no graphics card)
blender --background --python park_pals.py -- --render --frames 1 240       # only part of the film
```
Videos are saved in `renders/`.

**Option C: plain Python.** `pip install bpy` gives you Blender as a Python module (needs Python 3.11),
then `python park_pals.py --render --engine cycles`.

## Writing your own film

A film script has four parts: **set**, **cast**, **screenplay**, **finish**. See `my_first_film.py`.

### Time works like a screenplay
Each character action starts when the previous line finishes. To make things happen at the same time:
```python
with film.together():
    max_.walk_to(-4, 1.8)      # Max walks, then looks around...
    max_.play("look_around")
    lily.walk_to(2.2, 0.2)     # ...while Lily does the same
    lily.play("look_around")
```
Camera moves, `film.time_of_day()` and `film.wiggle()` **don't** wait. They start and the story carries on.

### Positions
Meters on the ground: `(x, y)`. The camera usually looks from the front (−y) toward the back (+y).
Kids are about 1.35 m tall, adults about 1.75 m.

### Characters
```python
ned = Character(film, "Ned", build="kid",            # "kid" or "adult"
                skin="#f3cfb3", shirt="#1d1d22", pants="#2d3550", shoes="#d93a3a",
                top="hoodie",                        # tshirt, hoodie, cardigan, suit
                bottom="pants",                      # pants, shorts, skirt
                hair="#6b4a2b", hair_style="buzz",   # short, buzz, long, ponytail, bun, bald
                cap="#c62828", cap_backwards=True, sunglasses=True, chain=True,
                face={"lids": 0.65, "smirk": 0.45})  # default expression
# more accessories: glasses="#color", tie="#color", mustache=True, backpack="#color"
# body shape: scale=0.9 (smaller), width=1.2 (wider)

ned.place(x, y, face=(x2, y2))          # put somewhere instantly
ned.walk_to(x, y, style="swagger")      # normal, swagger, run, sneak
ned.face(other_or_xy)                   # turn the body (the head leads)
ned.look_at(other_or_xyz)               # turn just the head (up/down too)
ned.play("cool_nod")                    # any move from the library
ned.say("Two bucks.", gesture="shrug")  # subtitle + talking mouth (+ optional move)
ned.set_face(smirk=0.9, glasses=1.0)    # change expression (glasses=1 lowers sunglasses)
ned.sit(0.34)   ned.stand()             # sit on something 0.34 m tall
ned.give(candy, tyler)                  # hand a prop to someone
ned.hold(obj)   ned.pocket(obj)         # hold a prop / put it away
ned.wait(1.5)                           # pause (handy inside film.together())
ned.pose({"arm_r": {"forward": 90}}, seconds=0.4)   # a custom pose that stays
```
**How they move:** feet stay planted (knees bend automatically), walks are built from real
footsteps with hip sway and shoulder swing, heads and arms follow a moment after the body,
and everyone breathes, blinks and glances around on their own. Chains and ponytails swing.

**Moves:** wave, cheer, jump, kick, point, point_up, think, sad, shrug, nod, cool_nod, shake_head,
look_around, sneaky_look, surprised, gasp, dance, bow, talk, clap, arms_crossed, lean_back,
count_money, hand_out, whisper, facepalm, sigh, swag. Make your own in `filmkit/moves.py`;
the file explains how poses work.

### Camera
```python
film.camera.close_up(sam, angle=20)          # head and shoulders
film.camera.medium(sam)                      # waist up
film.camera.hero(sam)                        # low angle looking up: makes them look important
film.camera.two_shot(sam, lily)              # both in frame
film.camera.over_shoulder(sam, lily)         # behind Sam, looking at Lily
film.camera.wide(center, distance=14, height=4, angle=0)
film.camera.orbit(center, radius=8, height=3, duration=6, start=0, end=90)
film.camera.follow(sam, offset=(2, -7, 2))   # tracks a walking character
film.camera.move(position, look_at, duration=2)
film.camera.shake(0.08, 0.5)
```
Every shot takes `duration=` (0 = hard cut, more = smooth camera move) and `delay=`.

### Set pieces (`props`)
`ground`, `path`, `tree` (returns the leafy top), `bush`, `house`, `bench`, `lamp`, `fence`,
`flowers`, `ball`, `rock`, `candy`, `cash`, `cash_pile`, `crate`. Move things with
`film.move(obj, (x, y, z), seconds, style="bounce")`, shake them with `film.wiggle(obj)`, resize with
`film.grow(obj, 1.5)` and make them disappear/appear with `film.hide(obj)` / `film.show(obj)`.

### Titles, effects and sound
```python
film.title("PARK PALS", "Episode 1", seconds=3)
film.caption("Maplewood Elementary. 7:58 AM.", seconds=3)   # narration at the top of the screen
film.black(); film.fade_in(1.5); film.fade_out(2)
film.credits(["Starring", "Max", "Lily"], seconds=8)
film.time_of_day(17.6, seconds=6)            # slow sunset
film.music("song.mp3", volume=0.6)           # your own music/sound files
```

### Checking a single shot
Rendering a whole film takes a while. To check one moment quickly:
```python
film.finish()
film.snapshot("check.png", seconds=42.5)
```

## Render engines
- **EEVEE** (default): much faster than Cycles, but needs a graphics card. (Not tested here: this project was rendered on a machine without one.)
- **Cycles** (`--engine cycles`): runs on any computer's CPU. Slower (about 1–2.5 s per preview frame
  on a 4-core machine, more for indoor scenes) but works everywhere.
