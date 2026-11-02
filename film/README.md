# Film Studio (animated films with code)

A small engine for making animated films in Roblox entirely with code, plus an example
short film, **"Park Pals - Episode 1: The Missing Ball"**. It's one LocalScript in plain Lua 5.1,
so it runs in **Studio Lite**.

## Setup (new place)

Create a **LocalScript** in **StarterPlayer → StarterPlayerScripts** and paste in
`FilmStudio.client.lua`. Press Play, then tap **PLAY FILM**.

## What the engine does

- **Actors**: characters built from code that walk, run, turn, act out moves and talk
  (speech bubbles + subtitles with a typewriter effect).
- **Camera**: close-ups, medium shots, two-shots, over-the-shoulder, wide shots, orbits,
  follow-cams and camera shake. Each one can be a hard cut or a smooth move.
- **Effects**: letterbox bars, fade in/out, title cards, scrolling credits, time of day.
- **Set pieces**: ground, paths, trees, benches, lamps, houses, fences, flowers, balls.

## Making your own episode

Edit section **2. YOUR FILM** at the bottom of the script:

1. **Cast**: `local Sam = Film.Actor("Sam", { Shirt = ..., Pants = ..., Hair = ..., LongHair = true })`
2. **Set**: place props with `Film.Props.*` using `S(x, z)` positions.
3. **Screenplay**: write the film as a list of steps:

```lua
Film.CloseUp(Sam, 0)                 -- cut to a close-up
Sam:Say("Where am I?", nil, "LookAround")
Film.Wide(S(0, 0), 25, 6, 0, 3)      -- slow camera move to a wide shot
Sam:WalkTo(S(10, -5))
```

The full cheat sheet is at the top of the script.
