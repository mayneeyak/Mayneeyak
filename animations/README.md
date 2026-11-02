# Character Moves (code-only animations)

Character animations made purely with code: no Animation Editor and no uploaded
animation IDs. It tweens each character's Motor6D joints, so it works on **R6 and R15**
avatars, and it's plain Lua 5.1 so it runs in **Studio Lite**.

## Setup (new place)

| File | Create this in Studio | Where |
|---|---|---|
| `CharacterMovesServer.server.lua` | **Script** | ServerScriptService |
| `CharacterMovesClient.client.lua` | **LocalScript** | StarterPlayer → StarterPlayerScripts |

Press Play. A **Dancer** on a purple stage performs the whole series on a loop, and the
**Moves** panel (top right) lets you perform any move with your own character.

## Moves

Wave, Cheer, Groove, Bow, Punch Combo, Spin, Kick, Jumping Jacks, Look Around, Flex.

## Making your own move

Add an entry to the `MOVES` table in the server script:

```lua
{
	Name = "Salute",
	Frames = {
		-- frame(seconds, pose, easingStyle?, holdSeconds?)
		frame(0.3, { RightShoulder = { 0, 0, 150 }, RightElbow = { 0, 0, 80 } }, QUAD, 1),
	},
},
```

Each joint takes `{ rx, ry, rz, ox, oy, oz }`, which are rotations in degrees, then optional offsets in studs.
Any joint you leave out goes back to rest. The direction cheat sheet is at the top of the server script.
The button for a new move shows up in the panel automatically.
