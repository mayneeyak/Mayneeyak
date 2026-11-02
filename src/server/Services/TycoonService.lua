--[[
	TycoonService
	Builds the plots, gives each player one, and runs the production line:

		Dropper  --drop-->  Conveyor  --(Upgraders multiply value)-->  Collector  --> Cash

	Purchase buttons appear on the owner's plot once the item they require
	is owned. Stepping on a button buys it.
]]

local Debris = game:GetService("Debris")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.TycoonConfig)
local Format = require(ReplicatedStorage.Shared.Format)
local DataService = require(script.Parent.DataService)

local TycoonService = {}

local Layout = Config.Layout

local plots = {}
local plotByPlayer = {}
local itemsById = {}
local notifyRemote

-- [dropPart] = { Value = number, Collected = bool, Upgraded = { [itemId] = true } }
-- Weak keys so destroyed drops get cleaned up automatically.
local dropInfo = setmetatable({}, { __mode = "k" })

for _, item in ipairs(Config.Items) do
	assert(itemsById[item.Id] == nil, "Duplicate tycoon item Id: " .. item.Id)
	itemsById[item.Id] = item
end

-- Helpers ---------------------------------------------------------------------

local function makePart(parent, props)
	local part = Instance.new("Part")
	part.Anchored = true
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	for key, value in pairs(props) do
		part[key] = value
	end
	part.Parent = parent
	return part
end

-- CFrame of a point relative to the plot's floor centre.
local function at(plot, x, y, z)
	return plot.CFrame * CFrame.new(x, y, z)
end

local function notify(player, message, kind)
	notifyRemote:FireClient(player, message, kind or "Info")
end

local function addLabel(parent, text)
	local label = Instance.new("TextLabel")
	label.Size = UDim2.new(1, 0, 1, 0)
	label.BackgroundTransparency = 1
	label.TextScaled = true
	label.Font = Enum.Font.FredokaOne
	label.TextColor3 = Color3.new(1, 1, 1)
	label.TextStrokeTransparency = 0.3
	label.Text = text
	label.Parent = parent
	return label
end

-- Drops -----------------------------------------------------------------------

local function spawnDrop(plot, item, spawnCFrame)
	if #plot.Drops:GetChildren() >= Config.MaxDropsPerPlot then
		return
	end

	local drop = makePart(plot.Drops, {
		Name = "Drop",
		Anchored = false,
		Size = Vector3.new(1, 1, 1),
		CFrame = spawnCFrame,
		Color = item.DropColor or Color3.new(0.5, 0.5, 0.5),
		Material = Enum.Material.SmoothPlastic,
	})
	dropInfo[drop] = { Value = item.DropValue, Collected = false, Upgraded = {} }

	-- Keep drop physics on the server so clients can't fling them around.
	pcall(function()
		drop:SetNetworkOwner(nil)
	end)

	Debris:AddItem(drop, Config.DropLifetime)
end

-- Item builders ---------------------------------------------------------------

local builders = {}

function builders.Dropper(plot, item, model)
	local z = Layout.ConveyorZ
	local x = item.X

	makePart(model, {
		Name = "Pillar",
		Size = Vector3.new(1.5, 10, 1.5),
		CFrame = at(plot, x, 5, z - 4.5),
		Color = Color3.fromRGB(60, 60, 60),
		Material = Enum.Material.Metal,
	})
	makePart(model, {
		Name = "Arm",
		Size = Vector3.new(1.5, 1, 4.5),
		CFrame = at(plot, x, 9.5, z - 2.25),
		Color = Color3.fromRGB(60, 60, 60),
		Material = Enum.Material.Metal,
	})
	local body = makePart(model, {
		Name = "Body",
		Size = Vector3.new(3, 3, 3),
		CFrame = at(plot, x, 8, z),
		Color = item.Color,
		Material = Enum.Material.Metal,
	})
	model.PrimaryPart = body

	-- Drop loop. Stops when the plot is released (Session changes).
	local session = plot.Session
	local spawnCFrame = at(plot, x, 5.5, z)
	task.spawn(function()
		while plot.Session == session and model.Parent do
			task.wait(item.DropInterval)
			if plot.Session ~= session or not model.Parent then
				break
			end
			spawnDrop(plot, item, spawnCFrame)
		end
	end)
end

function builders.Upgrader(plot, item, model)
	local z = Layout.ConveyorZ
	local x = item.X
	local frameColor = Color3.fromRGB(45, 45, 45)

	for _, side in ipairs({ -1, 1 }) do
		makePart(model, {
			Name = "Post",
			Size = Vector3.new(1, 6, 1),
			CFrame = at(plot, x, 3, z + side * 4.5),
			Color = frameColor,
			Material = Enum.Material.Metal,
		})
	end
	makePart(model, {
		Name = "TopBar",
		Size = Vector3.new(1, 1, 10),
		CFrame = at(plot, x, 6.5, z),
		Color = frameColor,
		Material = Enum.Material.Metal,
	})

	local field = makePart(model, {
		Name = "Field",
		Size = Vector3.new(1, 5, Layout.ConveyorWidth),
		CFrame = at(plot, x, 3.5, z),
		Color = item.Color,
		Material = Enum.Material.Neon,
		Transparency = 0.5,
		CanCollide = false,
	})
	model.PrimaryPart = field

	field.Touched:Connect(function(hit)
		local info = dropInfo[hit]
		if not info or hit.Parent ~= plot.Drops or info.Upgraded[item.Id] then
			return
		end
		info.Upgraded[item.Id] = true
		info.Value = info.Value * item.Multiplier
		hit.Color = item.Color
		hit.Material = Enum.Material.Neon
	end)
end

function builders.Decor(plot, item, model)
	for index, spec in ipairs(item.Parts) do
		makePart(model, {
			Name = "Part" .. index,
			Size = spec.Size,
			CFrame = at(plot, spec.Offset.X, spec.Offset.Y, spec.Offset.Z),
			Color = spec.Color or item.Color or Color3.new(1, 1, 1),
			Material = spec.Material or item.Material or Enum.Material.SmoothPlastic,
		})
	end
end

local function buildItem(plot, item)
	local builder = builders[item.Kind]
	if not builder then
		warn("[TycoonService] Unknown item kind: " .. tostring(item.Kind))
		return
	end

	local model = Instance.new("Model")
	model.Name = item.Id
	model.Parent = plot.Items
	builder(plot, item, model)
end

-- Buttons ---------------------------------------------------------------------

local function createButton(plot, item, index)
	local x = Layout.ButtonStartX + (index - 1) * Layout.ButtonSpacing
	local button = makePart(plot.ButtonFolder, {
		Name = item.Id .. "Button",
		Size = Vector3.new(5, 1, 5),
		CFrame = at(plot, x, 0.5, Layout.ButtonRowZ),
		Color = Color3.fromRGB(0, 200, 90),
		Material = Enum.Material.Neon,
	})

	local billboard = Instance.new("BillboardGui")
	billboard.Size = UDim2.new(7, 0, 2.5, 0)
	billboard.StudsOffset = Vector3.new(0, 3, 0)
	billboard.MaxDistance = 80
	billboard.Parent = button
	local priceText = item.Price > 0 and Format.cash(item.Price) or "FREE"
	addLabel(billboard, item.Name .. "\n" .. priceText)

	local debounce = false
	button.Touched:Connect(function(hit)
		if debounce then
			return
		end
		local player = Players:GetPlayerFromCharacter(hit.Parent)
		if not player or player ~= plot.Owner then
			return
		end
		local humanoid = hit.Parent:FindFirstChildOfClass("Humanoid")
		if not humanoid or humanoid.Health <= 0 then
			return
		end

		debounce = true
		TycoonService.TryPurchase(player, item.Id)
		task.delay(1, function()
			debounce = false
		end)
	end)

	return button
end

-- Shows buttons whose requirement is met and that aren't owned yet.
local function refreshButtons(plot)
	local owner = plot.Owner
	for index, item in ipairs(Config.Items) do
		local shouldShow = owner ~= nil
			and not DataService.Owns(owner, item.Id)
			and (item.Requires == nil or DataService.Owns(owner, item.Requires))

		local existing = plot.Buttons[item.Id]
		if shouldShow and not existing then
			plot.Buttons[item.Id] = createButton(plot, item, index)
		elseif not shouldShow and existing then
			existing:Destroy()
			plot.Buttons[item.Id] = nil
		end
	end
end

-- Plot base -------------------------------------------------------------------

local function buildPlot(parent, index)
	local offsetX = (index - 1 - (Config.PlotCount - 1) / 2) * Config.PlotSpacing
	local plot = {
		Index = index,
		CFrame = CFrame.new(offsetX, 0.5, 0),
		Owner = nil,
		Session = 0,
		Buttons = {},
		CharacterConn = nil,
	}

	local model = Instance.new("Model")
	model.Name = "Plot" .. index
	model.Parent = parent
	plot.Model = model

	local floor = makePart(model, {
		Name = "Floor",
		Size = Config.PlotSize,
		CFrame = at(plot, 0, -Config.PlotSize.Y / 2, 0),
		Color = Color3.fromRGB(75, 151, 75),
		Material = Enum.Material.Grass,
	})
	model.PrimaryPart = floor

	-- Conveyor: an anchored part with a velocity moves whatever sits on it.
	local length = Layout.ConveyorEndX - Layout.ConveyorStartX
	local centreX = (Layout.ConveyorStartX + Layout.ConveyorEndX) / 2
	local conveyor = makePart(model, {
		Name = "Conveyor",
		Size = Vector3.new(length, 1, Layout.ConveyorWidth),
		CFrame = at(plot, centreX, 0.5, Layout.ConveyorZ),
		Color = Color3.fromRGB(40, 40, 40),
		Material = Enum.Material.DiamondPlate,
	})
	local beltVelocity = plot.CFrame.RightVector * Config.ConveyorSpeed
	if not pcall(function()
		conveyor.AssemblyLinearVelocity = beltVelocity
	end) then
		conveyor.Velocity = beltVelocity -- older API name
	end

	local halfWidth = Layout.ConveyorWidth / 2
	for _, side in ipairs({ -1, 1 }) do
		makePart(model, {
			Name = "Rail",
			Size = Vector3.new(length, 2.5, 0.5),
			CFrame = at(plot, centreX, 1.25, Layout.ConveyorZ + side * (halfWidth + 0.25)),
			Color = Color3.fromRGB(255, 200, 0),
			Material = Enum.Material.Metal,
		})
	end

	-- Collector: turns drops into cash for the plot owner.
	local collector = makePart(model, {
		Name = "Collector",
		Size = Vector3.new(6, 3, Layout.ConveyorWidth + 2),
		CFrame = at(plot, Layout.ConveyorEndX + 3, 1.5, Layout.ConveyorZ),
		Color = Color3.fromRGB(255, 60, 60),
		Material = Enum.Material.Neon,
	})
	collector.Touched:Connect(function(hit)
		local info = dropInfo[hit]
		if not info or hit.Parent ~= plot.Drops or info.Collected then
			return
		end
		info.Collected = true
		local owner = plot.Owner
		if owner then
			DataService.AddCash(owner, info.Value)
		end
		hit:Destroy()
	end)

	-- Owner sign, readable from both sides.
	local sign = makePart(model, {
		Name = "Sign",
		Size = Vector3.new(24, 6, 1),
		CFrame = at(plot, 0, 3, 58),
		Color = Color3.fromRGB(30, 30, 30),
	})
	local signLabels = {}
	for _, face in ipairs({ Enum.NormalId.Front, Enum.NormalId.Back }) do
		local surface = Instance.new("SurfaceGui")
		surface.Face = face
		surface.CanvasSize = Vector2.new(600, 150)
		surface.Parent = sign
		table.insert(signLabels, addLabel(surface, ""))
	end
	plot.SignLabels = signLabels

	local function folder(name)
		local f = Instance.new("Folder")
		f.Name = name
		f.Parent = model
		return f
	end
	plot.Items = folder("Items")
	plot.ButtonFolder = folder("Buttons")
	plot.Drops = folder("Drops")

	return plot
end

local function setSignText(plot, text)
	for _, label in ipairs(plot.SignLabels) do
		label.Text = text
	end
end

-- Public API --------------------------------------------------------------------

function TycoonService.Init()
	local remotes = Instance.new("Folder")
	remotes.Name = "TycoonRemotes"
	notifyRemote = Instance.new("RemoteEvent")
	notifyRemote.Name = "Notify"
	notifyRemote.Parent = remotes
	remotes.Parent = ReplicatedStorage

	local container = Instance.new("Folder")
	container.Name = "Tycoons"
	container.Parent = workspace

	for index = 1, Config.PlotCount do
		local plot = buildPlot(container, index)
		setSignText(plot, "Unclaimed")
		plots[index] = plot
	end
end

function TycoonService.AssignPlot(player)
	if plotByPlayer[player] then
		return plotByPlayer[player]
	end

	local plot = nil
	for _, candidate in ipairs(plots) do
		if not candidate.Owner then
			plot = candidate
			break
		end
	end
	if not plot then
		notify(player, "All tycoons are taken right now. Try another server!", "Error")
		return nil
	end

	plot.Owner = player
	plot.Session = plot.Session + 1
	plotByPlayer[player] = plot
	setSignText(plot, player.DisplayName .. "'s Tycoon")

	-- Rebuild everything the player already owns.
	for _, item in ipairs(Config.Items) do
		if DataService.Owns(player, item.Id) then
			buildItem(plot, item)
		end
	end
	refreshButtons(plot)

	-- Spawn the player at their plot.
	local spawnPosition = at(plot, Config.SpawnOffset.X, Config.SpawnOffset.Y, Config.SpawnOffset.Z).Position
	-- Face toward the back of the plot (the production line).
	local spawnCFrame = CFrame.new(spawnPosition, spawnPosition + plot.CFrame.LookVector)
	local function onCharacter(character)
		local root = character:WaitForChild("HumanoidRootPart", 10)
		if not root or plot.Owner ~= player then
			return
		end
		task.wait() -- let the default spawn placement finish first
		root.CFrame = spawnCFrame
	end
	plot.CharacterConn = player.CharacterAdded:Connect(onCharacter)
	if player.Character then
		task.spawn(onCharacter, player.Character)
	end

	notify(player, "Welcome to your tycoon!", "Success")
	return plot
end

function TycoonService.ReleasePlot(player)
	local plot = plotByPlayer[player]
	if not plot then
		return
	end
	plotByPlayer[player] = nil

	plot.Session = plot.Session + 1 -- stops dropper loops
	plot.Owner = nil
	if plot.CharacterConn then
		plot.CharacterConn:Disconnect()
		plot.CharacterConn = nil
	end

	plot.Items:ClearAllChildren()
	plot.ButtonFolder:ClearAllChildren()
	plot.Drops:ClearAllChildren()
	plot.Buttons = {}
	setSignText(plot, "Unclaimed")
end

function TycoonService.TryPurchase(player, itemId)
	local plot = plotByPlayer[player]
	local item = itemsById[itemId]
	if not plot or not item then
		return false
	end
	if DataService.Owns(player, itemId) then
		return false
	end
	if item.Requires and not DataService.Owns(player, item.Requires) then
		return false
	end

	if not DataService.TrySpend(player, item.Price) then
		local missing = item.Price - DataService.GetCash(player)
		notify(player, ("You need %s more for %s"):format(Format.cash(missing), item.Name), "Error")
		return false
	end

	DataService.SetOwned(player, itemId)
	buildItem(plot, item)
	refreshButtons(plot)
	notify(player, "Purchased " .. item.Name .. "!", "Success")
	return true
end

return TycoonService
