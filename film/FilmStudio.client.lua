--[[
	FILM STUDIO  (plain Lua 5.1, works in Studio Lite)
	Put this in: StarterPlayer > StarterPlayerScripts  (as a LocalScript)

	A small engine for making animated films with code, plus an example
	short film ("Park Pals - Episode 1"). Press Play, then tap PLAY FILM.

	The file has three parts:
	  1. ENGINE      - actors, camera, effects, set pieces (no need to edit)
	  2. YOUR FILM   - the cast, the set, and the screenplay  <-- edit this!
	  3. START       - the Play button

	------------------------------------------------------------------------
	CHEAT SHEET (use these inside the Screenplay function)
	------------------------------------------------------------------------
	Things that TAKE TIME and wait until they finish:
	  actor:WalkTo(position)            actor:RunTo(position)
	  actor:Face(positionOrActor)       actor:Play("Wave")
	  actor:Say("Hello!")               actor:Say("Hi!", seconds, "Wave")
	  actor:Pose({ ...pose... }, time)  actor:Rest()
	  Film.Wait(seconds)                Film.FadeIn(t) / Film.FadeOut(t)
	  Film.Title("Big text", "small text", seconds)
	  Film.Credits({ "line", "line" }, seconds)
	  Film.Move(part, cframe, seconds, easingStyle)

	Things that START and let the film carry on (camera + effects):
	  Film.CloseUp(actor, time, angle)        Film.MediumShot(actor, time, angle)
	  Film.TwoShot(actorA, actorB, time)      Film.OverShoulder(fromActor, toActor, time)
	  Film.Wide(center, distance, height, angle, time)
	  Film.Camera(fromPosition, lookAtPosition, time, fov)
	  Film.Orbit(center, radius, height, seconds, startAngle, endAngle)
	  Film.Follow(actor, offset, seconds)     Film.Shake(strength, seconds)
	  Film.Letterbox(true/false, time)        Film.TimeOfDay(hour, seconds)
	  Film.Wiggle(part, amount, seconds)
	  (time = 0 is a hard CUT, time > 0 is a smooth camera move)

	Doing two things at once:
	  Film.Together(function() Max:WalkTo(a) end, function() Lily:WalkTo(b) end)
	  Film.Async(function() Lily:Play("Kick") end)   -- start it and keep going

	Moves: Wave, Cheer, Jump, Kick, Point, PointUp, Think, Sad, Shrug, Nod,
	       ShakeHead, LookAround, Surprised, Dance, Bow, Talk
]]

local Players = game:GetService("Players")
local TweenService = game:GetService("TweenService")
local Lighting = game:GetService("Lighting")
local StarterGui = game:GetService("StarterGui")

-- Fallback for editors without the newer "task" library.
local task = task or {
	wait = wait,
	delay = delay,
	spawn = function(fn, ...)
		local args = { ... }
		local count = select("#", ...)
		coroutine.wrap(function()
			fn(unpack(args, 1, count))
		end)()
	end,
}

local player = Players.LocalPlayer
local camera = workspace.CurrentCamera

--############################################################################
-- 1. ENGINE
--############################################################################

local Film = {}
Film.ShowBubbles = true -- speech bubbles above heads
Film.ShowSubtitles = true -- subtitles at the bottom of the screen

local SINE = Enum.EasingStyle.Sine
local QUAD = Enum.EasingStyle.Quad
local LINEAR = Enum.EasingStyle.Linear
local BACK = Enum.EasingStyle.Back
local BOUNCE = Enum.EasingStyle.Bounce

local function tween(object, time, props, style, direction)
	local info = TweenInfo.new(time, style or SINE, direction or Enum.EasingDirection.InOut)
	local t = TweenService:Create(object, info, props)
	t:Play()
	return t
end

local function flat(v)
	return Vector3.new(v.X, 0, v.Z)
end

local function positionOf(target)
	if type(target) == "table" and target.Root then
		return target.Root.Position
	end
	return target
end

function Film.Wait(seconds)
	task.wait(seconds)
end

function Film.Async(fn)
	task.spawn(fn)
end

-- Runs every function at the same time and waits for all of them.
function Film.Together(...)
	local fns = { ... }
	local remaining = #fns
	for i = 1, #fns do
		local fn = fns[i]
		task.spawn(function()
			fn()
			remaining = remaining - 1
		end)
	end
	while remaining > 0 do
		task.wait()
	end
end

-- Smoothly moves any part (props, balls, doors...). Waits until done.
function Film.Move(part, cframe, seconds, style)
	tween(part, seconds, { CFrame = cframe }, style or SINE, Enum.EasingDirection.Out)
	task.wait(seconds)
end

-- Shakes a part back and forth (leaves, signs...). Doesn't wait.
function Film.Wiggle(part, amount, seconds)
	local base = part.CFrame
	local swings = math.max(1, math.floor(seconds / 0.16))
	local info = TweenInfo.new(0.08, LINEAR, Enum.EasingDirection.InOut, swings, true)
	local t = TweenService:Create(part, info, { CFrame = base * CFrame.new(amount, 0, 0) })
	t:Play()
	task.delay(seconds + 0.2, function()
		part.CFrame = base
	end)
end

function Film.TimeOfDay(hour, seconds)
	if seconds and seconds > 0 then
		pcall(function()
			tween(Lighting, seconds, { ClockTime = hour }, LINEAR)
		end)
	else
		pcall(function()
			Lighting.ClockTime = hour
		end)
	end
end

------------------------------------------------------------------------------
-- Screen effects (letterbox, fades, titles, subtitles, credits)
------------------------------------------------------------------------------

local gui = Instance.new("ScreenGui")
gui.Name = "FilmStudio"
gui.ResetOnSpawn = false
pcall(function()
	gui.IgnoreGuiInset = true
end)

local function makeBar(anchorY, posY)
	local bar = Instance.new("Frame")
	bar.AnchorPoint = Vector2.new(0, anchorY)
	bar.Position = UDim2.new(0, 0, posY, 0)
	bar.Size = UDim2.new(1, 0, 0, 0)
	bar.BackgroundColor3 = Color3.new(0, 0, 0)
	bar.BorderSizePixel = 0
	bar.ZIndex = 1
	bar.Parent = gui
	return bar
end

local topBar = makeBar(0, 0)
local bottomBar = makeBar(1, 1)

local subtitle = Instance.new("TextLabel")
subtitle.AnchorPoint = Vector2.new(0.5, 1)
subtitle.Position = UDim2.new(0.5, 0, 1, -8)
subtitle.Size = UDim2.new(0.9, 0, 0.08, 0)
subtitle.BackgroundTransparency = 1
subtitle.TextScaled = true
subtitle.Font = Enum.Font.GothamBold
subtitle.TextColor3 = Color3.new(1, 1, 1)
subtitle.TextStrokeTransparency = 0.2
subtitle.Text = ""
subtitle.ZIndex = 4
subtitle.Parent = gui

local fade = Instance.new("Frame")
fade.Size = UDim2.new(1, 0, 1, 0)
fade.BackgroundColor3 = Color3.new(0, 0, 0)
fade.BackgroundTransparency = 1
fade.BorderSizePixel = 0
fade.ZIndex = 5
fade.Parent = gui

local function makeTitleLabel(posY, height, font)
	local label = Instance.new("TextLabel")
	label.AnchorPoint = Vector2.new(0.5, 0.5)
	label.Position = UDim2.new(0.5, 0, posY, 0)
	label.Size = UDim2.new(0.85, 0, height, 0)
	label.BackgroundTransparency = 1
	label.TextScaled = true
	label.Font = font
	label.TextColor3 = Color3.new(1, 1, 1)
	label.TextTransparency = 1
	label.TextStrokeTransparency = 1
	label.Text = ""
	label.ZIndex = 6
	label.Parent = gui
	return label
end

local titleLabel = makeTitleLabel(0.42, 0.16, Enum.Font.FredokaOne)
local subTitleLabel = makeTitleLabel(0.56, 0.07, Enum.Font.GothamBold)

local creditsLabel = Instance.new("TextLabel")
creditsLabel.AnchorPoint = Vector2.new(0.5, 0)
creditsLabel.BackgroundTransparency = 1
creditsLabel.Font = Enum.Font.GothamBold
creditsLabel.TextSize = 26
creditsLabel.TextColor3 = Color3.new(1, 1, 1)
creditsLabel.TextYAlignment = Enum.TextYAlignment.Top
creditsLabel.Visible = false
creditsLabel.ZIndex = 7
creditsLabel.Parent = gui

function Film.Letterbox(on, time)
	local size = on and UDim2.new(1, 0, 0.11, 0) or UDim2.new(1, 0, 0, 0)
	if not time or time <= 0 then
		topBar.Size = size
		bottomBar.Size = size
	else
		tween(topBar, time, { Size = size })
		tween(bottomBar, time, { Size = size })
	end
end

function Film.Black()
	fade.BackgroundTransparency = 0
end

function Film.FadeOut(seconds)
	tween(fade, seconds or 1, { BackgroundTransparency = 0 })
	task.wait(seconds or 1)
end

function Film.FadeIn(seconds)
	tween(fade, seconds or 1, { BackgroundTransparency = 1 })
	task.wait(seconds or 1)
end

function Film.Title(text, smallText, seconds)
	titleLabel.Text = text or ""
	subTitleLabel.Text = smallText or ""
	for _, label in ipairs({ titleLabel, subTitleLabel }) do
		tween(label, 0.6, { TextTransparency = 0, TextStrokeTransparency = 0.5 })
	end
	task.wait(0.6 + (seconds or 2))
	for _, label in ipairs({ titleLabel, subTitleLabel }) do
		tween(label, 0.6, { TextTransparency = 1, TextStrokeTransparency = 1 })
	end
	task.wait(0.6)
end

function Film.Credits(lines, seconds)
	seconds = seconds or 8
	local height = #lines * 36
	creditsLabel.Text = table.concat(lines, "\n")
	creditsLabel.Size = UDim2.new(0.9, 0, 0, height)
	creditsLabel.Position = UDim2.new(0.5, 0, 1, 0)
	creditsLabel.Visible = true
	tween(creditsLabel, seconds, { Position = UDim2.new(0.5, 0, 0, -height) }, LINEAR)
	task.wait(seconds)
	creditsLabel.Visible = false
end

local function showSubtitle(name, text)
	if Film.ShowSubtitles then
		subtitle.Text = string.upper(name) .. ":  " .. text
	end
end

local function hideSubtitle()
	subtitle.Text = ""
end

------------------------------------------------------------------------------
-- Camera
------------------------------------------------------------------------------

local cameraJob = 0
local cameraTween = nil

-- Every new camera command cancels the previous one.
local function newCameraJob()
	cameraJob = cameraJob + 1
	if cameraTween then
		cameraTween:Cancel()
		cameraTween = nil
	end
	camera.CameraType = Enum.CameraType.Scriptable
	return cameraJob
end

function Film.Camera(from, at, time, fov)
	newCameraJob()
	local target = CFrame.new(from, at)
	if not time or time <= 0 then
		camera.CFrame = target
		if fov then
			camera.FieldOfView = fov
		end
	else
		local props = { CFrame = target }
		if fov then
			props.FieldOfView = fov
		end
		cameraTween = tween(camera, time, props)
	end
end

function Film.CloseUp(actor, time, angle, fov)
	local head = actor:HeadPosition()
	local dir = CFrame.Angles(0, math.rad(angle or 0), 0) * actor.Root.CFrame.LookVector
	Film.Camera(head + dir * 4.5 + Vector3.new(0, 0.3, 0), head - Vector3.new(0, 0.1, 0), time, fov or 45)
end

function Film.MediumShot(actor, time, angle, fov)
	local center = actor.Root.Position + Vector3.new(0, 0.8, 0)
	local dir = CFrame.Angles(0, math.rad(angle or 0), 0) * actor.Root.CFrame.LookVector
	Film.Camera(center + dir * 10 + Vector3.new(0, 1, 0), center, time, fov or 55)
end

-- Both actors in frame, side-on. side = 1 or -1 picks which side (optional).
function Film.TwoShot(a, b, time, side, fov)
	local pa, pb = a.Root.Position, b.Root.Position
	local mid = (pa + pb) / 2
	local diff = flat(pb - pa)
	local dir = diff.Magnitude > 0 and diff.Unit or Vector3.new(1, 0, 0)
	local perp = Vector3.new(-dir.Z, 0, dir.X)
	if side then
		perp = perp * side
	elseif perp.Z < 0 then
		perp = -perp -- default: film from the "audience" side (+Z)
	end
	local distance = math.max(9, diff.Magnitude * 1.4)
	Film.Camera(mid + perp * distance + Vector3.new(0, 1.5, 0), mid + Vector3.new(0, 0.8, 0), time, fov or 55)
end

function Film.OverShoulder(fromActor, toActor, time, fov)
	local pf = fromActor.Root.Position
	local dir = flat(toActor.Root.Position - pf).Unit
	local right = Vector3.new(-dir.Z, 0, dir.X)
	Film.Camera(pf - dir * 3.5 + right * 1.6 + Vector3.new(0, 2.2, 0), toActor:HeadPosition(), time, fov or 50)
end

function Film.Wide(center, distance, height, angle, time, fov)
	local offset = CFrame.Angles(0, math.rad(angle or 0), 0) * Vector3.new(0, 0, distance)
	Film.Camera(center + offset + Vector3.new(0, height, 0), center, time, fov or 60)
end

function Film.Orbit(center, radius, height, seconds, startAngle, endAngle, fov)
	local job = newCameraJob()
	if fov then
		camera.FieldOfView = fov
	end
	startAngle = startAngle or 0
	endAngle = endAngle or 360
	task.spawn(function()
		local startTime = os.clock()
		while cameraJob == job do
			local alpha = math.min((os.clock() - startTime) / seconds, 1)
			local r = math.rad(startAngle + (endAngle - startAngle) * alpha)
			local from = center + Vector3.new(math.sin(r) * radius, height, math.cos(r) * radius)
			camera.CFrame = CFrame.new(from, center)
			if alpha >= 1 then
				break
			end
			task.wait()
		end
	end)
end

function Film.Follow(actor, offset, seconds, fov)
	local job = newCameraJob()
	if fov then
		camera.FieldOfView = fov
	end
	task.spawn(function()
		local startTime = os.clock()
		while cameraJob == job and os.clock() - startTime < seconds do
			local pos = actor.Root.Position
			camera.CFrame = CFrame.new(pos + offset, pos + Vector3.new(0, 1, 0))
			task.wait()
		end
	end)
end

function Film.Shake(strength, seconds)
	local job = newCameraJob()
	local base = camera.CFrame
	task.spawn(function()
		local startTime = os.clock()
		while cameraJob == job and os.clock() - startTime < seconds do
			local fadeOut = 1 - (os.clock() - startTime) / seconds
			local s = strength * fadeOut
			camera.CFrame = base * CFrame.new((math.random() - 0.5) * s, (math.random() - 0.5) * s, 0)
			task.wait()
		end
		if cameraJob == job then
			camera.CFrame = base
		end
	end)
end

------------------------------------------------------------------------------
-- Moves (keyframed poses)
------------------------------------------------------------------------------
--[[
	A pose gives joints { rx, ry, rz, ox, oy, oz } (degrees, then studs).
	Joints: Root, Neck, RightShoulder, LeftShoulder, RightHip, LeftHip
	  Arms/legs: rx+ forward, rx- back, rz+ out to the right, rz- out to the left
	  Neck:      rx+ look up, rx- look down, ry+ turn left, ry- turn right
	  Root:      rx- lean forward, rx+ lean back, ry turn, oy move body up/down
	Joints left out of a pose go back to rest.
]]

local function frame(time, pose, style, hold)
	return { Time = time, Pose = pose or {}, Style = style, Hold = hold }
end

local REST = {}

local MOVES = {
	Wave = { Frames = {
		frame(0.25, { RightShoulder = { 0, 0, 175 }, Neck = { 0, 0, -8 } }),
		frame(0.18, { RightShoulder = { 0, 0, 135 }, Neck = { 0, 0, -8 } }),
		frame(0.18, { RightShoulder = { 0, 0, 175 }, Neck = { 0, 0, -8 } }),
		frame(0.18, { RightShoulder = { 0, 0, 135 }, Neck = { 0, 0, -8 } }),
		frame(0.18, { RightShoulder = { 0, 0, 175 }, Neck = { 0, 0, -8 } }),
	} },
	Cheer = { Repeat = 3, Frames = {
		frame(0.2, { RightShoulder = { 0, 0, 170 }, LeftShoulder = { 0, 0, -170 }, Neck = { 15, 0, 0 }, Root = { 0, 0, 0, 0, 0.8, 0 } }, QUAD),
		frame(0.2, { RightShoulder = { 0, 0, 145 }, LeftShoulder = { 0, 0, -145 }, Neck = { 10, 0, 0 } }, QUAD),
	} },
	Jump = { Frames = {
		frame(0.15, { Root = { -10, 0, 0, 0, -0.4, 0 }, RightHip = { 25, 0, 0 }, LeftHip = { 25, 0, 0 }, RightShoulder = { -30, 0, 0 }, LeftShoulder = { -30, 0, 0 } }, QUAD),
		frame(0.25, { Root = { 0, 0, 0, 0, 2.2, 0 }, RightHip = { 20, 0, 0 }, LeftHip = { 20, 0, 0 }, RightShoulder = { 0, 0, 160 }, LeftShoulder = { 0, 0, -160 }, Neck = { 20, 0, 0 } }, QUAD),
		frame(0.25, { Root = { 0, 0, 0, 0, 0, 0 } }, QUAD),
	} },
	Kick = { Frames = {
		frame(0.25, { RightHip = { -30, 0, 0 }, Root = { 5, 0, 0 }, LeftHip = { -5, 0, 0 }, RightShoulder = { 30, 0, -10 }, LeftShoulder = { 30, 0, 10 } }),
		frame(0.12, { RightHip = { 95, 0, 0 }, Root = { 15, 0, 0 }, LeftHip = { -15, 0, 0 }, RightShoulder = { -30, 0, 25 }, LeftShoulder = { -30, 0, -25 } }, BACK, 0.25),
	} },
	Point = { Frames = {
		frame(0.25, { RightShoulder = { 90, 0, 0 }, Neck = { 0, 0, 0 } }, QUAD, 0.9),
	} },
	PointUp = { Frames = {
		frame(0.3, { RightShoulder = { 150, 0, 10 }, Neck = { 25, 0, 0 } }, QUAD, 1.2),
	} },
	Think = { Frames = {
		frame(0.4, { RightShoulder = { 105, 0, -35 }, LeftShoulder = { 40, 0, 30 }, Neck = { 10, 0, 10 } }, QUAD, 1.3),
	} },
	Sad = { Frames = {
		frame(0.6, { Neck = { -30, 0, 0 }, RightShoulder = { 5, 0, -3 }, LeftShoulder = { 5, 0, 3 }, Root = { -8, 0, 0, 0, -0.1, 0 }, RightHip = { 8, 0, 0 }, LeftHip = { 8, 0, 0 } }, SINE, 1.2),
	} },
	Shrug = { Frames = {
		frame(0.25, { RightShoulder = { 20, 0, 40 }, LeftShoulder = { 20, 0, -40 }, Neck = { 0, 0, 15 } }, QUAD, 0.7),
	} },
	Nod = { Frames = {
		frame(0.15, { Neck = { -20, 0, 0 } }),
		frame(0.15, { Neck = { 5, 0, 0 } }),
		frame(0.15, { Neck = { -20, 0, 0 } }),
	} },
	ShakeHead = { Repeat = 2, Frames = {
		frame(0.15, { Neck = { 0, 30, 0 } }),
		frame(0.15, { Neck = { 0, -30, 0 } }),
	} },
	LookAround = { Frames = {
		frame(0.5, { Neck = { 0, 60, 0 }, Root = { 0, 10, 0 } }, QUAD, 0.3),
		frame(0.7, { Neck = { 0, -60, 0 }, Root = { 0, -10, 0 } }, QUAD, 0.3),
	} },
	Surprised = { Frames = {
		frame(0.15, { Root = { 12, 0, 0 }, RightHip = { -12, 0, 0 }, LeftHip = { -12, 0, 0 }, RightShoulder = { 30, 0, 60 }, LeftShoulder = { 30, 0, -60 }, Neck = { 15, 0, 0 } }, BACK, 0.6),
	} },
	Dance = { Repeat = 4, Frames = {
		frame(0.28, { RightShoulder = { 60, 0, 30 }, LeftShoulder = { -20, 0, -20 }, Neck = { 0, 0, -10 }, Root = { 0, 12, 6, 0.3, 0, 0 }, RightHip = { 0, -12, -6 }, LeftHip = { 0, -12, -6 } }),
		frame(0.28, { RightShoulder = { -20, 0, 20 }, LeftShoulder = { 60, 0, -30 }, Neck = { 0, 0, 10 }, Root = { 0, -12, -6, -0.3, 0, 0 }, RightHip = { 0, 12, 6 }, LeftHip = { 0, 12, 6 } }),
	} },
	Bow = { Frames = {
		frame(0.5, { Root = { -45, 0, 0 }, RightHip = { 45, 0, 0 }, LeftHip = { 45, 0, 0 }, RightShoulder = { 70, 0, -35 }, LeftShoulder = { -25, 0, 0 }, Neck = { -15, 0, 0 } }, QUAD, 0.7),
	} },
	Talk = { Repeat = 2, Frames = {
		frame(0.3, { RightShoulder = { 35, 0, 10 }, Neck = { 5, 0, 0 } }),
		frame(0.3, { LeftShoulder = { 35, 0, -10 }, Neck = { 0, 0, 0 } }),
	} },
}

-- Add your own move from the film section: Film.AddMove("Salute", { Frames = {...} })
function Film.AddMove(name, move)
	MOVES[name] = move
end
Film.frame = frame

------------------------------------------------------------------------------
-- Actors (R6 characters built from code)
------------------------------------------------------------------------------

local Actor = {}
Actor.__index = Actor

-- Standard R6 joints: { motor name, part0, part1, C0, C1 }
local R6_JOINTS = {
	Root = { "RootJoint", "HumanoidRootPart", "Torso",
		CFrame.new(0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0), CFrame.new(0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0) },
	Neck = { "Neck", "Torso", "Head",
		CFrame.new(0, 1, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0), CFrame.new(0, -0.5, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0) },
	RightShoulder = { "Right Shoulder", "Torso", "Right Arm",
		CFrame.new(1, 0.5, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0), CFrame.new(-0.5, 0.5, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0) },
	LeftShoulder = { "Left Shoulder", "Torso", "Left Arm",
		CFrame.new(-1, 0.5, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0), CFrame.new(0.5, 0.5, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0) },
	RightHip = { "Right Hip", "Torso", "Right Leg",
		CFrame.new(1, -1, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0), CFrame.new(0.5, 1, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0) },
	LeftHip = { "Left Hip", "Torso", "Left Leg",
		CFrame.new(-1, -1, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0), CFrame.new(-0.5, 1, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0) },
}

local function makeBodyPart(model, name, size, color)
	local part = Instance.new("Part")
	part.Name = name
	part.Size = size
	part.Color = color
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	part.CanCollide = false
	part.Parent = model
	return part
end

local function weldTo(model, head, name, size, color, offset)
	local part = makeBodyPart(model, name, size, color)
	part.CFrame = head.CFrame * offset
	local weld = Instance.new("Weld")
	weld.Part0 = head
	weld.Part1 = part
	weld.C0 = offset
	weld.Parent = part
	return part
end

-- look = { Skin, Shirt, Pants, Hair, LongHair, Face }
function Film.Actor(name, look)
	look = look or {}
	local skin = look.Skin or Color3.fromRGB(255, 204, 153)
	local shirt = look.Shirt or Color3.fromRGB(0, 140, 255)
	local pants = look.Pants or Color3.fromRGB(40, 40, 60)

	local model = Instance.new("Model")
	model.Name = name

	local parts = {
		HumanoidRootPart = makeBodyPart(model, "HumanoidRootPart", Vector3.new(2, 2, 1), skin),
		Torso = makeBodyPart(model, "Torso", Vector3.new(2, 2, 1), shirt),
		Head = makeBodyPart(model, "Head", Vector3.new(2, 1, 1), skin),
		["Right Arm"] = makeBodyPart(model, "Right Arm", Vector3.new(1, 2, 1), skin),
		["Left Arm"] = makeBodyPart(model, "Left Arm", Vector3.new(1, 2, 1), skin),
		["Right Leg"] = makeBodyPart(model, "Right Leg", Vector3.new(1, 2, 1), pants),
		["Left Leg"] = makeBodyPart(model, "Left Leg", Vector3.new(1, 2, 1), pants),
	}
	local root = parts.HumanoidRootPart
	root.Transparency = 1
	root.Anchored = true
	root.CFrame = CFrame.new(0, 50, 0)
	for _, part in pairs(parts) do
		part.CFrame = root.CFrame
	end

	local headMesh = Instance.new("SpecialMesh")
	headMesh.MeshType = Enum.MeshType.Head
	headMesh.Scale = Vector3.new(1.25, 1.25, 1.25)
	headMesh.Parent = parts.Head

	local face = Instance.new("Decal")
	face.Name = "face"
	face.Texture = look.Face or "rbxasset://textures/face.png"
	face.Face = Enum.NormalId.Front
	face.Parent = parts.Head

	local self = setmetatable({}, Actor)
	self.Name = name
	self.Model = model
	self.Root = root
	self.Head = parts.Head
	self.FaceDecal = face
	self.Joints = {}
	self.RestC0 = {}

	for jointName, spec in pairs(R6_JOINTS) do
		local motor = Instance.new("Motor6D")
		motor.Name = spec[1]
		motor.Part0 = parts[spec[2]]
		motor.Part1 = parts[spec[3]]
		motor.C0 = spec[4]
		motor.C1 = spec[5]
		motor.Parent = parts[spec[2]]
		self.Joints[jointName] = motor
		self.RestC0[jointName] = spec[4]
	end

	if look.Hair then
		weldTo(model, parts.Head, "Hair", Vector3.new(2.1, 0.45, 1.15), look.Hair, CFrame.new(0, 0.62, 0))
		if look.LongHair then
			weldTo(model, parts.Head, "LongHair", Vector3.new(2.1, 1.5, 0.4), look.Hair, CFrame.new(0, -0.05, 0.6))
		end
	end

	-- Speech bubble
	local bubble = Instance.new("BillboardGui")
	bubble.Size = UDim2.new(0, 240, 0, 64)
	bubble.StudsOffset = Vector3.new(0, 2.6, 0)
	bubble.AlwaysOnTop = true
	bubble.Enabled = false
	bubble.Parent = parts.Head

	local bubbleFrame = Instance.new("Frame")
	bubbleFrame.Size = UDim2.new(1, 0, 1, 0)
	bubbleFrame.BackgroundColor3 = Color3.new(1, 1, 1)
	bubbleFrame.Parent = bubble
	Instance.new("UICorner", bubbleFrame).CornerRadius = UDim.new(0, 12)

	local bubbleText = Instance.new("TextLabel")
	bubbleText.Position = UDim2.new(0, 8, 0, 4)
	bubbleText.Size = UDim2.new(1, -16, 1, -8)
	bubbleText.BackgroundTransparency = 1
	bubbleText.TextScaled = true
	bubbleText.TextWrapped = true
	bubbleText.Font = Enum.Font.GothamBold
	bubbleText.TextColor3 = Color3.new(0.1, 0.1, 0.1)
	bubbleText.Text = ""
	bubbleText.Parent = bubbleFrame

	self.Bubble = bubble
	self.BubbleText = bubbleText

	model.PrimaryPart = root
	model.Parent = workspace
	return self
end

function Actor:HeadPosition()
	return self.Root.Position + Vector3.new(0, 1.5, 0)
end

-- Turns a joint around its pivot, in the parent part's directions.
local function posedC0(rest, spec)
	if not spec then
		return rest
	end
	local rotation = CFrame.Angles(math.rad(spec[1] or 0), math.rad(spec[2] or 0), math.rad(spec[3] or 0))
	local offset = Vector3.new(spec[4] or 0, spec[5] or 0, spec[6] or 0)
	return CFrame.new(rest.p + offset) * rotation * (rest - rest.p)
end

-- Starts tweening every joint toward the pose (doesn't wait).
function Actor:ApplyPose(pose, time, style)
	for jointName, motor in pairs(self.Joints) do
		local goal = posedC0(self.RestC0[jointName], pose[jointName])
		if time and time > 0 then
			tween(motor, time, { C0 = goal }, style or SINE)
		else
			motor.C0 = goal
		end
	end
end

-- Holds a pose until the next action.
function Actor:Pose(pose, time)
	self:ApplyPose(pose, time or 0.3)
	task.wait(time or 0.3)
end

function Actor:Rest(time)
	self:Pose(REST, time or 0.3)
end

function Actor:Play(move)
	if type(move) == "string" then
		local found = MOVES[move]
		if not found then
			warn("[Film] No move called " .. move)
			return
		end
		move = found
	end
	for _ = 1, move.Repeat or 1 do
		for _, f in ipairs(move.Frames) do
			self:ApplyPose(f.Pose, f.Time, f.Style)
			task.wait(f.Time + (f.Hold or 0))
		end
	end
	if not move.Stay then
		self:Rest(0.3)
	end
end

-- Instantly puts the actor somewhere (good for the start of a scene).
function Actor:Place(position, lookAt)
	local pos = Vector3.new(position.X, position.Y + 3, position.Z)
	local target = lookAt and positionOf(lookAt) or (pos + Vector3.new(0, 0, -1))
	self.Root.CFrame = CFrame.new(pos, Vector3.new(target.X, pos.Y, target.Z))
	self:ApplyPose(REST, 0)
	self.Bubble.Enabled = false
end

function Actor:Face(target, time)
	time = time or 0.3
	local pos = self.Root.Position
	local t = positionOf(target)
	if (flat(t) - flat(pos)).Magnitude < 0.05 then
		return
	end
	tween(self.Root, time, { CFrame = CFrame.new(pos, Vector3.new(t.X, pos.Y, t.Z)) })
	task.wait(time)
end

function Actor:WalkTo(target, speed)
	speed = speed or 8
	local start = self.Root.Position
	local goal = Vector3.new(target.X, start.Y, target.Z)
	local distance = (goal - start).Magnitude
	if distance < 0.05 then
		return
	end
	self:Face(goal, 0.2)

	local swing = 25 + speed
	local step = math.max(0.16, 2.6 / speed)
	local walking = true
	task.spawn(function()
		local s = 1
		while walking do
			self:ApplyPose({
				RightHip = { swing * s, 0, 0 },
				LeftHip = { -swing * s, 0, 0 },
				RightShoulder = { -swing * 0.8 * s, 0, 0 },
				LeftShoulder = { swing * 0.8 * s, 0, 0 },
				Root = { 0, 0, 0, 0, 0.1, 0 },
			}, step)
			task.wait(step)
			s = -s
		end
	end)

	local walkTime = distance / speed
	tween(self.Root, walkTime, { CFrame = CFrame.new(goal, goal + (goal - start).Unit) }, LINEAR)
	task.wait(walkTime)
	walking = false
	self:Rest(0.2)
end

function Actor:RunTo(target)
	self:WalkTo(target, 18)
end

-- Says a line. Optional: seconds to stay on screen, and a move to do while talking.
function Actor:Say(text, seconds, gesture)
	seconds = seconds or (1.4 + #text * 0.06)
	if Film.ShowBubbles then
		self.BubbleText.Text = ""
		self.Bubble.Enabled = true
	end
	showSubtitle(self.Name, text)
	if gesture then
		task.spawn(function()
			self:Play(gesture)
		end)
	end

	local typeTime = math.min(#text * 0.03, seconds * 0.6)
	local perChar = typeTime / math.max(#text, 1)
	for i = 1, #text do
		self.BubbleText.Text = string.sub(text, 1, i)
		task.wait(perChar)
	end
	task.wait(seconds - typeTime)

	self.Bubble.Enabled = false
	hideSubtitle()
end

-- Use your own face decal: actor:SetFace("rbxassetid://123456")
function Actor:SetFace(texture)
	self.FaceDecal.Texture = texture
end

------------------------------------------------------------------------------
-- Set pieces
------------------------------------------------------------------------------

Film.Props = {}
local setFolder = Instance.new("Folder")
setFolder.Name = "FilmSet"
setFolder.Parent = workspace

function Film.Part(props)
	local part = Instance.new("Part")
	part.Anchored = true
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	for key, value in pairs(props) do
		if key ~= "Parent" then
			part[key] = value
		end
	end
	part.Parent = props.Parent or setFolder
	return part
end

local function at(pos, rotation, x, y, z)
	return CFrame.new(pos) * CFrame.Angles(0, math.rad(rotation or 0), 0) * CFrame.new(x, y, z)
end

function Film.Props.Ground(center, size, color)
	return Film.Part({
		Name = "Ground",
		Size = size,
		CFrame = CFrame.new(center - Vector3.new(0, size.Y / 2, 0)),
		Color = color or Color3.fromRGB(90, 160, 70),
		Material = Enum.Material.Grass,
	})
end

function Film.Props.Path(from, to, width)
	local mid = (from + to) / 2
	local length = (flat(to) - flat(from)).Magnitude
	return Film.Part({
		Name = "Path",
		Size = Vector3.new(width or 6, 0.2, length),
		CFrame = CFrame.new(mid + Vector3.new(0, 0.1, 0), to + Vector3.new(0, 0.1, 0)),
		Color = Color3.fromRGB(215, 190, 140),
		Material = Enum.Material.Sand,
	})
end

function Film.Props.Tree(pos, height)
	height = height or 12
	local trunk = Film.Part({
		Name = "Trunk",
		Size = Vector3.new(2, height, 2),
		CFrame = CFrame.new(pos + Vector3.new(0, height / 2, 0)),
		Color = Color3.fromRGB(105, 70, 40),
		Material = Enum.Material.Wood,
	})
	local leaves = Film.Part({
		Name = "Leaves",
		Shape = Enum.PartType.Ball,
		Size = Vector3.new(12, 12, 12),
		CFrame = CFrame.new(pos + Vector3.new(0, height + 2, 0)),
		Color = Color3.fromRGB(60, 140, 50),
		Material = Enum.Material.Grass,
	})
	return trunk, leaves
end

function Film.Props.Bench(pos, rotation)
	local wood = Color3.fromRGB(150, 100, 60)
	Film.Part({ Name = "Seat", Size = Vector3.new(6, 0.4, 2), CFrame = at(pos, rotation, 0, 1.6, 0), Color = wood, Material = Enum.Material.Wood })
	Film.Part({ Name = "Back", Size = Vector3.new(6, 1.6, 0.3), CFrame = at(pos, rotation, 0, 2.6, 0.85), Color = wood, Material = Enum.Material.Wood })
	for _, x in ipairs({ -2.6, 2.6 }) do
		Film.Part({ Name = "Leg", Size = Vector3.new(0.4, 1.6, 1.8), CFrame = at(pos, rotation, x, 0.8, 0), Color = Color3.fromRGB(50, 50, 50), Material = Enum.Material.Metal })
	end
end

function Film.Props.Lamp(pos)
	Film.Part({ Name = "Pole", Size = Vector3.new(0.6, 10, 0.6), CFrame = CFrame.new(pos + Vector3.new(0, 5, 0)), Color = Color3.fromRGB(40, 40, 40), Material = Enum.Material.Metal })
	local bulb = Film.Part({ Name = "Bulb", Size = Vector3.new(1.4, 1.4, 1.4), CFrame = CFrame.new(pos + Vector3.new(0, 10.5, 0)), Color = Color3.fromRGB(255, 240, 180), Material = Enum.Material.Neon })
	pcall(function()
		local light = Instance.new("PointLight")
		light.Range = 18
		light.Brightness = 1.5
		light.Color = Color3.fromRGB(255, 230, 170)
		light.Parent = bulb
	end)
	return bulb
end

function Film.Props.House(pos, wallColor, roofColor, rotation)
	wallColor = wallColor or Color3.fromRGB(240, 220, 190)
	roofColor = roofColor or Color3.fromRGB(170, 60, 50)
	Film.Part({ Name = "Walls", Size = Vector3.new(16, 10, 12), CFrame = at(pos, rotation, 0, 5, 0), Color = wallColor, Material = Enum.Material.Brick })
	Film.Part({ Name = "Roof", Size = Vector3.new(18, 1.5, 14), CFrame = at(pos, rotation, 0, 10.75, 0), Color = roofColor })
	Film.Part({ Name = "RoofTop", Size = Vector3.new(12, 1.5, 9), CFrame = at(pos, rotation, 0, 12.25, 0), Color = roofColor })
	Film.Part({ Name = "Door", Size = Vector3.new(3, 6, 0.3), CFrame = at(pos, rotation, 0, 3, 6.1), Color = Color3.fromRGB(110, 70, 40), Material = Enum.Material.Wood })
	for _, x in ipairs({ -5, 5 }) do
		Film.Part({ Name = "Window", Size = Vector3.new(3, 3, 0.3), CFrame = at(pos, rotation, x, 6, 6.1), Color = Color3.fromRGB(150, 210, 255), Material = Enum.Material.Glass })
	end
end

function Film.Props.Fence(from, to)
	local length = (flat(to) - flat(from)).Magnitude
	local mid = (from + to) / 2
	local look = CFrame.new(mid, Vector3.new(to.X, mid.Y, to.Z))
	local white = Color3.fromRGB(245, 245, 245)
	for _, y in ipairs({ 1.2, 2.6 }) do
		Film.Part({ Name = "Rail", Size = Vector3.new(0.3, 0.4, length), CFrame = look * CFrame.new(0, y, 0), Color = white })
	end
	local posts = math.floor(length / 4)
	for i = 0, posts do
		local z = -length / 2 + i * (length / posts)
		Film.Part({ Name = "Post", Size = Vector3.new(0.5, 3.4, 0.5), CFrame = look * CFrame.new(0, 1.7, z), Color = white })
	end
end

function Film.Props.Flowers(center, count, radius)
	local colors = { Color3.fromRGB(255, 90, 120), Color3.fromRGB(255, 220, 60), Color3.fromRGB(180, 120, 255), Color3.fromRGB(255, 255, 255) }
	for i = 1, count do
		local angle = i * 2.4
		local r = radius * math.sqrt(i / count)
		local pos = center + Vector3.new(math.cos(angle) * r, 0, math.sin(angle) * r)
		Film.Part({ Name = "Stem", Size = Vector3.new(0.15, 0.8, 0.15), CFrame = CFrame.new(pos + Vector3.new(0, 0.4, 0)), Color = Color3.fromRGB(60, 140, 50), CanCollide = false })
		Film.Part({ Name = "Flower", Shape = Enum.PartType.Ball, Size = Vector3.new(0.6, 0.6, 0.6), CFrame = CFrame.new(pos + Vector3.new(0, 0.9, 0)), Color = colors[(i % #colors) + 1], Material = Enum.Material.SmoothPlastic, CanCollide = false })
	end
end

function Film.Props.Ball(pos, color, size)
	size = size or 1.6
	return Film.Part({
		Name = "Ball",
		Shape = Enum.PartType.Ball,
		Size = Vector3.new(size, size, size),
		CFrame = CFrame.new(pos),
		Color = color or Color3.fromRGB(230, 40, 40),
		Material = Enum.Material.SmoothPlastic,
		CanCollide = false,
	})
end

--############################################################################
-- 2. YOUR FILM  (edit everything below to make your own episodes!)
--############################################################################

-- The set is built far from the spawn so it doesn't get in the way.
local SET_CENTER = Vector3.new(0, 1, 400)

-- S(x, z, height) = a spot on the set, measured from its center.
-- +x is right, -z is toward the back (houses), +z is toward the camera.
local function S(x, z, height)
	return SET_CENTER + Vector3.new(x, height or 0, z)
end

-- CAST ------------------------------------------------------------------------

local Max = Film.Actor("Max", {
	Shirt = Color3.fromRGB(220, 60, 60),
	Pants = Color3.fromRGB(40, 60, 120),
	Hair = Color3.fromRGB(70, 45, 25),
})

local Lily = Film.Actor("Lily", {
	Skin = Color3.fromRGB(240, 190, 150),
	Shirt = Color3.fromRGB(255, 160, 200),
	Pants = Color3.fromRGB(90, 70, 160),
	Hair = Color3.fromRGB(245, 205, 90),
	LongHair = true,
})

-- SET -------------------------------------------------------------------------

Film.Props.Ground(SET_CENTER, Vector3.new(160, 1, 160))
Film.Props.Path(S(-70, 10), S(70, 10), 6)
local TREE_POS = S(14, -8)
local trunk, leaves = Film.Props.Tree(TREE_POS, 12)
Film.Props.Tree(S(-40, -20), 10)
Film.Props.Tree(S(40, -25), 14)
Film.Props.Bench(S(-12, -4), 0)
Film.Props.Lamp(S(-22, 5))
Film.Props.Lamp(S(24, 5))
Film.Props.House(S(-25, -38), Color3.fromRGB(240, 220, 190), Color3.fromRGB(170, 60, 50), 0)
Film.Props.House(S(18, -42), Color3.fromRGB(200, 225, 240), Color3.fromRGB(60, 80, 150), 0)
Film.Props.Fence(S(-70, -56), S(70, -56))
Film.Props.Flowers(S(-14, 20), 24, 5)
Film.Props.Flowers(S(26, 18), 18, 4)

local BALL_IN_TREE = S(11, -3, 13.5)
local ball = Film.Props.Ball(BALL_IN_TREE)

-- Starting positions (also used for the preview before you press Play).
local function resetScene()
	Film.TimeOfDay(9)
	Max:Place(S(-45, 10), S(0, 10))
	Lily:Place(S(45, 10), S(0, 10))
	ball.CFrame = CFrame.new(BALL_IN_TREE)
end
resetScene()

-- SCREENPLAY ------------------------------------------------------------------

local function Screenplay()
	resetScene()
	Film.Black()
	Film.Letterbox(true, 0)

	Film.Title("PARK PALS", "Episode 1: The Missing Ball", 2.5)

	-- SCENE 1: a sunny morning in the park
	Film.Orbit(S(0, 0, 4), 45, 16, 7, -50, 15)
	Film.FadeIn(1.5)
	Film.Wait(3)

	-- Max walks in, looking for something
	Film.Follow(Max, Vector3.new(4, 4, 16), 6)
	Max:WalkTo(S(-6, 3))
	Max:Face(S(0, 20))
	Film.CloseUp(Max, 0)
	Max:Play("LookAround")
	Max:Say("Has anyone seen my red ball?", nil, "Sad")

	-- Lily arrives
	Film.Wide(S(2, 3), 24, 5, 20, 0)
	Lily:WalkTo(S(4, 3))
	Film.Together(function()
		Lily:Face(Max)
	end, function()
		Max:Face(Lily)
	end)
	Film.TwoShot(Max, Lily, 0)
	Lily:Say("Hi Max! Why do you look so sad?", nil, "Wave")
	Film.OverShoulder(Lily, Max, 0)
	Max:Say("I lost my ball. I've looked everywhere!", nil, "Shrug")
	Film.OverShoulder(Max, Lily, 0)
	Lily:Say("Don't worry. Let's look together!", nil, "Nod")

	-- SCENE 2: the search
	Film.Wide(S(-2, 0), 30, 9, -10, 0)
	Film.Wide(S(-2, 0), 24, 6, 10, 5)
	Film.Together(function()
		Max:WalkTo(S(-14, -1))
		Max:Play("LookAround")
	end, function()
		Lily:WalkTo(S(4, -2))
		Lily:Play("LookAround")
	end)

	-- Lily spots it
	Film.MediumShot(Lily, 0, 30)
	Lily:Face(BALL_IN_TREE)
	Lily:Play("Surprised")
	Film.Camera(Lily:HeadPosition() + Vector3.new(-3, 0.5, 6), BALL_IN_TREE, 1.5, 40)
	Lily:Say("Look! It's stuck up in the tree!", nil, "PointUp")

	-- Max can't reach it
	Film.Wide(S(8, -2, 3), 20, 3, 0, 0)
	Max:RunTo(S(10, 0))
	Max:Face(BALL_IN_TREE)
	Max:Play("Jump")
	Max:Play("Jump")
	Film.CloseUp(Max, 0, -20)
	Max:Say("I can't reach it!", nil, "Sad")
	Film.CloseUp(Lily, 0, 20)
	Lily:Play("Think")
	Lily:Say("Hmm... I have an idea!", nil, "PointUp")

	-- SCENE 3: Lily kicks the tree
	Lily:WalkTo(S(14, -5))
	Lily:Face(TREE_POS)
	Film.Wide(S(12, -4, 4), 18, 3, 25, 0)
	Film.Async(function()
		Lily:Play("Kick")
	end)
	Film.Wait(0.35)
	Film.Shake(0.5, 0.6)
	Film.Wiggle(leaves, 0.4, 0.8)
	Film.Wait(0.3)
	Film.Move(ball, CFrame.new(S(11, -3, 0.8)), 1.2, BOUNCE)
	Film.Move(ball, CFrame.new(S(10, -1.3, 0.8)) * CFrame.Angles(0, 0, math.rad(170)), 0.6)

	-- The happy ending
	Film.CloseUp(Max, 0, -15)
	Max:Play("Surprised")
	Max:Say("My ball! You did it, Lily!", nil, "Cheer")
	Lily:Face(Max)
	Film.TwoShot(Max, Lily, 0)
	Lily:Say("That's what friends are for!", nil, "Wave")

	Film.TimeOfDay(17.8, 5)
	local middle = (Max.Root.Position + Lily.Root.Position) / 2
	Film.Orbit(middle, 14, 4, 7, 20, 140)
	Film.Together(function()
		Max:Play("Dance")
	end, function()
		Lily:Play("Dance")
	end)
	Film.Together(function()
		Max:Play("Bow")
	end, function()
		Lily:Play("Bow")
	end)

	Film.FadeOut(2)
	Film.Title("THE END", "", 2)
	Film.Credits({
		"PARK PALS",
		"",
		"Starring",
		"Max",
		"Lily",
		"and the Red Ball",
		"",
		"Made entirely with code",
		"",
		"Thanks for watching!",
	}, 9)
end

--############################################################################
-- 3. START  (the Play button)
--############################################################################

local playButton = Instance.new("TextButton")
playButton.AnchorPoint = Vector2.new(0.5, 1)
playButton.Position = UDim2.new(0.5, 0, 1, -30)
playButton.Size = UDim2.new(0, 220, 0, 56)
playButton.BackgroundColor3 = Color3.fromRGB(220, 50, 50)
playButton.TextColor3 = Color3.new(1, 1, 1)
playButton.Font = Enum.Font.FredokaOne
playButton.TextSize = 28
playButton.Text = "PLAY FILM"
playButton.ZIndex = 8
playButton.Parent = gui
Instance.new("UICorner", playButton).CornerRadius = UDim.new(0, 14)

gui.Parent = player:WaitForChild("PlayerGui")

-- Hides your own character (and the Roblox menus) while the film plays.
local function setPlayerHidden(hidden)
	local character = player.Character
	if character then
		for _, d in ipairs(character:GetDescendants()) do
			if d:IsA("BasePart") or d:IsA("Decal") then
				d.LocalTransparencyModifier = hidden and 1 or 0
			end
		end
		local root = character:FindFirstChild("HumanoidRootPart")
		if root then
			root.Anchored = hidden
		end
	end
	pcall(function()
		StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.All, not hidden)
	end)
end

local playing = false

local function playFilm()
	playing = true
	playButton.Visible = false
	setPlayerHidden(true)

	Screenplay()

	-- Back to normal
	newCameraJob()
	camera.CameraType = Enum.CameraType.Custom
	camera.FieldOfView = 70
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if humanoid then
		camera.CameraSubject = humanoid
	end
	Film.Letterbox(false, 0)
	fade.BackgroundTransparency = 1
	hideSubtitle()
	setPlayerHidden(false)
	resetScene()

	playButton.Text = "WATCH AGAIN"
	playButton.Visible = true
	playing = false
end

playButton.MouseButton1Click:Connect(function()
	if not playing then
		task.spawn(playFilm)
	end
end)
