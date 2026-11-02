# Tycoon (Roblox / Luau)

A complete, self-building tycoon for Roblox, set up as a [Rojo](https://rojo.space) project.
Everything (plots, conveyor, droppers, upgraders, buttons) is created by script, so it
works in an empty place with no pre-made models.

## How it plays

1. Each player gets their own plot when they join, and spawns on it.
2. Step on the green **buttons** to buy things. New buttons appear as you unlock items.
3. **Droppers** drop ore onto the **conveyor**.
4. **Upgraders** (glowing gates) multiply the value of each drop that passes through.
5. The red **collector** turns drops into **Cash** (shown on the leaderboard and HUD).
6. Cash and purchases save with DataStores and are rebuilt when you rejoin.

## Project layout

```
default.project.json              Rojo mapping into the Roblox DataModel
src/
  shared/                         -> ReplicatedStorage.Shared
    TycoonConfig.lua              All items, prices, layout & tuning numbers
    Format.lua                    1500 -> "$1.5K" number formatting
  server/                         -> ServerScriptService.Server
    Main.server.lua               Entry point: starts services, handles join/leave
    Services/
      DataService.lua             Load/save with retries, autosave, BindToClose, leaderstats
      TycoonService.lua           Plots, droppers, conveyor, upgraders, collector, buttons
  client/                         -> StarterPlayer.StarterPlayerScripts.Client
    HUD.client.lua                Cash display + purchase notifications
```

## Setup

1. Install the tools: [Rokit](https://github.com/rojo-rbx/rokit), then run `rokit install` in this folder
   (or install Rojo 7.4 another way).
2. Install the **Rojo** plugin in Roblox Studio.
3. Run `rojo serve` in this folder, then in Studio open the Rojo plugin and click **Connect**.
4. **Game Settings → Security → Enable Studio Access to API Services** (needed for saving in Studio;
   the game publishes and saves fine without it, it's only for testing).
5. **Game Settings → Places → Max Players** = `6` (matches `PlotCount` in the config).
6. Press **Play**.

To build a place file instead: `rojo build -o Tycoon.rbxl`.

## Adding your own items

Add an entry to `TycoonConfig.Items` in `src/shared/TycoonConfig.lua`:

```lua
{
	Id = "Dropper6",            -- saved to DataStore; never rename once published
	Name = "Emerald Dropper",
	Price = 40000,
	Requires = "Dropper5",      -- button appears once this is owned
	Kind = "Dropper",           -- "Dropper" | "Upgrader" | "Decor"
	X = 10,                     -- position along the conveyor (-45 .. 40)
	DropValue = 150,
	DropInterval = 1,
	Color = Color3.fromRGB(0, 200, 100),
	DropColor = Color3.fromRGB(80, 255, 150),
},
```

Keep droppers to the left of (lower X than) the upgraders so drops pass through them.

## No Rojo? Paste-ready version

`standalone/` has the whole game as two scripts you can paste straight into Studio:

| File | Create this in Studio | Where |
|---|---|---|
| `standalone/TycoonServer.server.lua` | **Script** | ServerScriptService |
| `standalone/TycoonHUD.client.lua` | **LocalScript** | StarterPlayer → StarterPlayerScripts |

These are written in plain Lua 5.1 (no type annotations or `+=`), so they also run in editors like Studio Lite. They are generated from the files in `src/`; if you change `src/`, update them too.
