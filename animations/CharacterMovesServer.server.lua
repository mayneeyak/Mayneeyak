--[[
	CHARACTER MOVES - SERVER  (plain Lua 5.1, works in Studio Lite)
	Put this in: ServerScriptService  (as a Script)
	Pair it with CharacterMovesClient in StarterPlayer > StarterPlayerScripts.

	Animates characters purely with code: no Animation Editor, no uploaded
	animation IDs. It works by tweening the C0 of each character's Motor6D
	joints, so it runs on both R6 and R15 avatars.

	What you get:
	  * A "Dancer" NPC on a stage that performs the whole move series forever.
	  * A move panel (from the client script) so players can perform any move
	    or the whole series with their own character. Everyone sees it.

	------------------------------------------------------------------------
	HOW TO WRITE A POSE
	------------------------------------------------------------------------
	A pose is a table of joints. Each joint gets { rx, ry, rz, ox, oy, oz }:
	  rx, ry, rz  rotation in degrees
	  ox, oy, oz  position offset in studs (optional, mostly for "Root")
	Any joint you leave out goes back to its normal resting position.

	Directions (same for R6 and R15):
	  Arms / legs:  rx +  = swing forward      rx - = swing back
	                rz +  = swing out to the RIGHT  (use + for the right arm/leg)
	                rz -  = swing out to the LEFT   (use - for the left arm/leg)
	  Neck:         rx +  = look up   rx - = look down   ry = turn   rz = tilt
	  Root (whole body):
	                rx -  = lean forward   rx + = lean back
	                ry +  = turn left      ry - = turn right
	                oy    = move body up (+) or down (-)

	Joints: Root, Neck, RightShoulder, LeftShoulder, RightHip, LeftHip
	R15 only (ignored on R6): Waist, RightElbow, LeftElbow, RightKnee, LeftKnee
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")

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

--============================================================================
-- MOVES
--============================================================================

-- frame(seconds, pose, easingStyle?, holdSeconds?)
local function frame(time, pose, style, hold)
	return { Time = time, Pose = pose or {}, Style = style, Hold = hold }
end

local QUAD = Enum.EasingStyle.Quad
local LINEAR = Enum.EasingStyle.Linear
local BACK = Enum.EasingStyle.Back

local REST = {}

-- Poses reused by several frames
local waveHigh = { RightShoulder = { 0, 0, 175 }, Neck = { 0, 0, -8 } }
local waveLow = { RightShoulder = { 0, 0, 135 }, Neck = { 0, 0, -8 } }

local guard = {
	RightShoulder = { 45, 0, -15 },
	LeftShoulder = { 45, 0, 15 },
	RightElbow = { 70, 0, 0 },
	LeftElbow = { 70, 0, 0 },
}

local MOVES = {
	{
		Name = "Wave",
		Frames = {
			frame(0.25, waveHigh),
			frame(0.18, waveLow),
			frame(0.18, waveHigh),
			frame(0.18, waveLow),
			frame(0.18, waveHigh),
			frame(0.18, waveLow),
		},
	},
	{
		Name = "Cheer",
		Repeat = 3,
		Frames = {
			frame(0.2, {
				RightShoulder = { 0, 0, 170 },
				LeftShoulder = { 0, 0, -170 },
				Neck = { 15, 0, 0 },
				Root = { 0, 0, 0, 0, 0.8, 0 },
			}, QUAD),
			frame(0.2, {
				RightShoulder = { 0, 0, 145 },
				LeftShoulder = { 0, 0, -145 },
				Neck = { 10, 0, 0 },
			}, QUAD),
		},
	},
	{
		Name = "Groove",
		Repeat = 4,
		Frames = {
			frame(0.28, {
				RightShoulder = { 60, 0, 30 },
				LeftShoulder = { -20, 0, -20 },
				Neck = { 0, 0, -10 },
				Root = { 0, 12, 6, 0.3, 0, 0 },
				RightHip = { 0, -12, -6 },
				LeftHip = { 0, -12, -6 },
			}),
			frame(0.28, {
				RightShoulder = { -20, 0, 20 },
				LeftShoulder = { 60, 0, -30 },
				Neck = { 0, 0, 10 },
				Root = { 0, -12, -6, -0.3, 0, 0 },
				RightHip = { 0, 12, 6 },
				LeftHip = { 0, 12, 6 },
			}),
		},
	},
	{
		Name = "Bow",
		Frames = {
			frame(0.5, {
				Root = { -45, 0, 0 },
				RightHip = { 45, 0, 0 },
				LeftHip = { 45, 0, 0 },
				RightShoulder = { 70, 0, -35 },
				RightElbow = { 60, 0, 0 },
				LeftShoulder = { -25, 0, 0 },
				Neck = { -15, 0, 0 },
			}, QUAD, 0.7),
		},
	},
	{
		Name = "Punch Combo",
		Repeat = 2,
		Frames = {
			frame(0.15, guard),
			frame(0.12, {
				RightShoulder = { 90, 0, 0 },
				LeftShoulder = { 45, 0, 15 },
				LeftElbow = { 70, 0, 0 },
				Root = { 0, 25, 0 },
				RightHip = { 0, -25, 0 },
				LeftHip = { 0, -25, 0 },
			}, QUAD),
			frame(0.15, guard),
			frame(0.12, {
				LeftShoulder = { 90, 0, 0 },
				RightShoulder = { 45, 0, -15 },
				RightElbow = { 70, 0, 0 },
				Root = { 0, -25, 0 },
				RightHip = { 0, 25, 0 },
				LeftHip = { 0, 25, 0 },
			}, QUAD),
		},
	},
	{
		Name = "Spin",
		Repeat = 2,
		Frames = {
			frame(0.18, { Root = { 0, 120, 0 }, RightShoulder = { 0, 0, 90 }, LeftShoulder = { 0, 0, -90 } }, LINEAR),
			frame(0.18, { Root = { 0, 240, 0 }, RightShoulder = { 0, 0, 90 }, LeftShoulder = { 0, 0, -90 } }, LINEAR),
			frame(0.18, { Root = { 0, 360, 0 }, RightShoulder = { 0, 0, 90 }, LeftShoulder = { 0, 0, -90 } }, LINEAR),
		},
	},
	{
		Name = "Kick",
		Frames = {
			frame(0.25, {
				RightHip = { -30, 0, 0 },
				Root = { 5, 0, 0 },
				LeftHip = { -5, 0, 0 },
				RightShoulder = { 30, 0, -10 },
				LeftShoulder = { 30, 0, 10 },
			}),
			frame(0.12, {
				RightHip = { 95, 0, 0 },
				Root = { 15, 0, 0 },
				LeftHip = { -15, 0, 0 },
				RightShoulder = { -30, 0, 25 },
				LeftShoulder = { -30, 0, -25 },
			}, BACK, 0.2),
		},
	},
	{
		Name = "Jumping Jacks",
		Repeat = 4,
		Frames = {
			frame(0.2, {
				RightShoulder = { 0, 0, 165 },
				LeftShoulder = { 0, 0, -165 },
				RightHip = { 0, 0, 20 },
				LeftHip = { 0, 0, -20 },
				Root = { 0, 0, 0, 0, 0.5, 0 },
			}, QUAD),
			frame(0.2, REST, QUAD),
		},
	},
	{
		Name = "Look Around",
		Frames = {
			frame(0.5, { Neck = { 0, 60, 0 }, Root = { 0, 10, 0 } }, QUAD, 0.3),
			frame(0.7, { Neck = { 0, -60, 0 }, Root = { 0, -10, 0 } }, QUAD, 0.3),
			frame(0.4, { Neck = { 25, 0, 0 } }, QUAD, 0.3),
		},
	},
	{
		Name = "Flex",
		Frames = {
			-- On R15 the elbows bend so the fists point up; on R6 the arms go straight out.
			frame(0.35, {
				RightShoulder = { 0, 0, 90 },
				LeftShoulder = { 0, 0, -90 },
				RightElbow = { 0, 0, 90 },
				LeftElbow = { 0, 0, -90 },
				Neck = { 10, 0, 0 },
				Root = { 0, 0, 0, 0, 0.2, 0 },
			}, BACK, 0.4),
			frame(0.2, {
				RightShoulder = { 0, 0, 100 },
				LeftShoulder = { 0, 0, -100 },
				RightElbow = { 0, 0, 110 },
				LeftElbow = { 0, 0, -110 },
				Neck = { 10, 0, 0 },
				Root = { 0, 0, 0, 0, 0.2, 0 },
			}, QUAD, 0.5),
		},
	},
}

local MOVES_BY_NAME = {}
for _, move in ipairs(MOVES) do
	MOVES_BY_NAME[move.Name] = move
end

--============================================================================
-- ANIMATOR
--============================================================================

-- Where each logical joint lives: { part name, Motor6D name }
local JOINT_PATHS = {
	R6 = {
		Root = { "HumanoidRootPart", "RootJoint" },
		Neck = { "Torso", "Neck" },
		RightShoulder = { "Torso", "Right Shoulder" },
		LeftShoulder = { "Torso", "Left Shoulder" },
		RightHip = { "Torso", "Right Hip" },
		LeftHip = { "Torso", "Left Hip" },
	},
	R15 = {
		Root = { "LowerTorso", "Root" },
		Waist = { "UpperTorso", "Waist" },
		Neck = { "Head", "Neck" },
		RightShoulder = { "RightUpperArm", "RightShoulder" },
		LeftShoulder = { "LeftUpperArm", "LeftShoulder" },
		RightElbow = { "RightLowerArm", "RightElbow" },
		LeftElbow = { "LeftLowerArm", "LeftElbow" },
		RightHip = { "RightUpperLeg", "RightHip" },
		LeftHip = { "LeftUpperLeg", "LeftHip" },
		RightKnee = { "RightLowerLeg", "RightKnee" },
		LeftKnee = { "LeftLowerLeg", "LeftKnee" },
	},
}

-- Weak keys: entries disappear when characters/joints are destroyed.
local restC0 = setmetatable({}, { __mode = "k" }) -- [Motor6D] = original C0
local playTokens = setmetatable({}, { __mode = "k" }) -- [character] = token of the running animation

local function getJoints(character)
	local paths = character:FindFirstChild("UpperTorso") and JOINT_PATHS.R15 or JOINT_PATHS.R6
	local joints = {}
	for jointName, path in pairs(paths) do
		local part = character:FindFirstChild(path[1])
		local motor = part and part:FindFirstChild(path[2])
		if motor and motor:IsA("Motor6D") then
			joints[jointName] = motor
			if not restC0[motor] then
				restC0[motor] = motor.C0
			end
		end
	end
	return joints
end

-- Rotates the joint around its pivot, in the parent part's directions, so
-- the same numbers mean the same thing on R6 and R15.
local function posedC0(rest, spec)
	if not spec then
		return rest
	end
	local rotation = CFrame.Angles(math.rad(spec[1] or 0), math.rad(spec[2] or 0), math.rad(spec[3] or 0))
	local offset = Vector3.new(spec[4] or 0, spec[5] or 0, spec[6] or 0)
	return CFrame.new(rest.p + offset) * rotation * (rest - rest.p)
end

local function applyPose(joints, pose, time, style)
	local info = TweenInfo.new(time, style or Enum.EasingStyle.Sine, Enum.EasingDirection.InOut)
	for jointName, motor in pairs(joints) do
		if motor.Parent then
			TweenService:Create(motor, info, { C0 = posedC0(restC0[motor], pose[jointName]) }):Play()
		end
	end
end

local Animator = {}

-- Plays a list of moves in order. Starting another animation (or Stop)
-- on the same character cancels this one.
-- onMoveStart(move) is called as each move begins (optional).
function Animator.Play(character, moveList, onMoveStart)
	local joints = getJoints(character)
	local token = {}
	playTokens[character] = token

	local function cancelled()
		return playTokens[character] ~= token or not character.Parent
	end

	for _, move in ipairs(moveList) do
		if cancelled() then
			return false
		end
		if onMoveStart then
			onMoveStart(move)
		end
		for _ = 1, move.Repeat or 1 do
			for _, f in ipairs(move.Frames) do
				if cancelled() then
					return false
				end
				applyPose(joints, f.Pose, f.Time, f.Style)
				task.wait(f.Time + (f.Hold or 0))
			end
		end
		if cancelled() then
			return false
		end
		applyPose(joints, REST, 0.3)
		task.wait(0.4)
	end

	if playTokens[character] == token then
		playTokens[character] = nil
	end
	return true
end

function Animator.Stop(character)
	playTokens[character] = nil
	applyPose(getJoints(character), REST, 0.25)
end

--============================================================================
-- DANCER NPC (an R6 rig built entirely from code)
--============================================================================

local function makeLimb(model, name, size, color)
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

local function makeMotor(name, part0, part1, c0, c1)
	local motor = Instance.new("Motor6D")
	motor.Name = name
	motor.Part0 = part0
	motor.Part1 = part1
	motor.C0 = c0
	motor.C1 = c1
	motor.Parent = part0
	return motor
end

local function buildDancer(rootCFrame)
	local skin = Color3.fromRGB(255, 204, 153)
	local shirt = Color3.fromRGB(0, 140, 255)
	local pants = Color3.fromRGB(40, 40, 60)

	local model = Instance.new("Model")
	model.Name = "Dancer"

	local root = makeLimb(model, "HumanoidRootPart", Vector3.new(2, 2, 1), skin)
	root.Transparency = 1
	root.Anchored = true
	root.CFrame = rootCFrame

	local torso = makeLimb(model, "Torso", Vector3.new(2, 2, 1), shirt)
	local head = makeLimb(model, "Head", Vector3.new(2, 1, 1), skin)
	local rightArm = makeLimb(model, "Right Arm", Vector3.new(1, 2, 1), skin)
	local leftArm = makeLimb(model, "Left Arm", Vector3.new(1, 2, 1), skin)
	local rightLeg = makeLimb(model, "Right Leg", Vector3.new(1, 2, 1), pants)
	local leftLeg = makeLimb(model, "Left Leg", Vector3.new(1, 2, 1), pants)

	-- Rough starting positions (the joints snap them into place).
	torso.CFrame = rootCFrame
	head.CFrame = rootCFrame * CFrame.new(0, 1.5, 0)
	rightArm.CFrame = rootCFrame * CFrame.new(1.5, 0, 0)
	leftArm.CFrame = rootCFrame * CFrame.new(-1.5, 0, 0)
	rightLeg.CFrame = rootCFrame * CFrame.new(0.5, -2, 0)
	leftLeg.CFrame = rootCFrame * CFrame.new(-0.5, -2, 0)

	local headMesh = Instance.new("SpecialMesh")
	headMesh.MeshType = Enum.MeshType.Head
	headMesh.Scale = Vector3.new(1.25, 1.25, 1.25)
	headMesh.Parent = head

	local face = Instance.new("Decal")
	face.Name = "face"
	face.Texture = "rbxasset://textures/face.png"
	face.Face = Enum.NormalId.Front
	face.Parent = head

	-- Standard R6 joint layout.
	makeMotor("RootJoint", root, torso,
		CFrame.new(0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0),
		CFrame.new(0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0))
	makeMotor("Neck", torso, head,
		CFrame.new(0, 1, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0),
		CFrame.new(0, -0.5, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0))
	makeMotor("Right Shoulder", torso, rightArm,
		CFrame.new(1, 0.5, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0),
		CFrame.new(-0.5, 0.5, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0))
	makeMotor("Left Shoulder", torso, leftArm,
		CFrame.new(-1, 0.5, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0),
		CFrame.new(0.5, 0.5, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0))
	makeMotor("Right Hip", torso, rightLeg,
		CFrame.new(1, -1, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0),
		CFrame.new(0.5, 1, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0))
	makeMotor("Left Hip", torso, leftLeg,
		CFrame.new(-1, -1, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0),
		CFrame.new(-0.5, 1, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0))

	local humanoid = Instance.new("Humanoid")
	humanoid.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
	humanoid.Parent = model

	model.PrimaryPart = root
	model.Parent = workspace

	-- Name tag showing the current move.
	local billboard = Instance.new("BillboardGui")
	billboard.Size = UDim2.new(8, 0, 1.5, 0)
	billboard.StudsOffset = Vector3.new(0, 2.5, 0)
	billboard.Parent = head

	local label = Instance.new("TextLabel")
	label.Size = UDim2.new(1, 0, 1, 0)
	label.BackgroundTransparency = 1
	label.TextScaled = true
	label.Font = Enum.Font.GothamBold
	label.TextColor3 = Color3.new(1, 1, 1)
	label.TextStrokeTransparency = 0.3
	label.Text = "Dancer"
	label.Parent = billboard

	return model, label
end

local function buildStage()
	local stage = Instance.new("Part")
	stage.Name = "Stage"
	stage.Anchored = true
	stage.Size = Vector3.new(14, 1, 14)
	stage.CFrame = CFrame.new(0, 0.5, -20)
	stage.Color = Color3.fromRGB(120, 60, 200)
	stage.Material = Enum.Material.Neon
	stage.TopSurface = Enum.SurfaceType.Smooth
	stage.Parent = workspace
	return stage
end

--============================================================================
-- START
--============================================================================

-- Remote + move list for the client panel (built fully before parenting).
local remotes = Instance.new("Folder")
remotes.Name = "CharacterMoves"

local playRemote = Instance.new("RemoteEvent")
playRemote.Name = "PlayMove"
playRemote.Parent = remotes

local moveList = Instance.new("Folder")
moveList.Name = "MoveList"
moveList.Parent = remotes
for index, move in ipairs(MOVES) do
	local entry = Instance.new("StringValue")
	entry.Name = string.format("%02d", index)
	entry.Value = move.Name
	entry.Parent = moveList
end

remotes.Parent = ReplicatedStorage

-- Players asking to perform moves.
local lastRequest = {}

playRemote.OnServerEvent:Connect(function(player, action, moveName)
	local now = os.clock()
	if lastRequest[player] and now - lastRequest[player] < 0.2 then
		return
	end
	lastRequest[player] = now

	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if not humanoid or humanoid.Health <= 0 then
		return
	end

	if action == "Move" and type(moveName) == "string" and MOVES_BY_NAME[moveName] then
		task.spawn(Animator.Play, character, { MOVES_BY_NAME[moveName] })
	elseif action == "Series" then
		task.spawn(Animator.Play, character, MOVES)
	elseif action == "Stop" then
		Animator.Stop(character)
	end
end)

Players.PlayerRemoving:Connect(function(player)
	lastRequest[player] = nil
end)

-- The Dancer performs the whole series on a loop, facing the spawn.
buildStage()
local dancerRoot = CFrame.new(0, 4, -20) * CFrame.Angles(0, math.pi, 0)
local dancer, dancerLabel = buildDancer(dancerRoot)

task.spawn(function()
	task.wait(1) -- let the rig settle
	while dancer.Parent do
		Animator.Play(dancer, MOVES, function(move)
			dancerLabel.Text = move.Name
		end)
		dancerLabel.Text = "Dancer"
		task.wait(1.5)
	end
end)
