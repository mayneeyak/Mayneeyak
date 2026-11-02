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
Characters are about 1.75 m tall.

### Characters
```python
sam = Character(film, "Sam", skin="#f2c29b", shirt="#ff7043", pants="#37474f",
                hair="#212121", long_hair=False, scale=1.0)   # scale=0.7 for a kid
sam.place(x, y, face=(x2, y2))       # put somewhere instantly
sam.walk_to(x, y)    sam.run_to(x, y)
sam.face(other_or_xy)                # turn the body
sam.look_at(other_or_xyz)            # turn just the head (up/down too)
sam.play("wave")                     # any move from the library
sam.say("Hi!", gesture="nod")        # subtitle + talking mouth (+ optional move)
sam.pose({"arm_r": {"forward": 90}}, seconds=0.4)   # a custom pose that stays
sam.rest()
```
**Moves:** wave, cheer, jump, kick, point, point_up, think, sad, shrug, nod, shake_head,
look_around, surprised, dance, bow, talk, clap. Make your own in `filmkit/moves.py`; the file explains how poses work.

### Camera
```python
film.camera.close_up(sam, angle=20)          # face fills the frame
film.camera.medium(sam)                      # waist up
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
`flowers`, `ball`, `rock`. Move things with `film.move(obj, (x, y, z), seconds, style="bounce")`
and shake them with `film.wiggle(obj)`.

### Titles, effects and sound
```python
film.title("PARK PALS", "Episode 1", seconds=3)
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
- **Cycles** (`--engine cycles`): runs on any computer's CPU. Slower (about 1.5 s per preview frame
  on a 4-core machine) but works everywhere.
