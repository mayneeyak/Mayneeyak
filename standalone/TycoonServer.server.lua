--[[
	TYCOON - SERVER SCRIPT (all-in-one)
	Put this in: ServerScriptService  (as a normal Script, NOT a LocalScript)
	Pair it with the TycoonHUD LocalScript in StarterPlayer > StarterPlayerScripts.
]]

local DataStoreService = game:GetService("DataStoreService")
local Debris = game:GetService("Debris")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local TycoonConfig = {}

-- Economy / saving ---------------------------------------------------------
TycoonConfig.StartingCash = 0
TycoonConfig.DataStoreName = "TycoonData_v1"
TycoonConfig.AutosaveInterval = 120 -- seconds

-- Plots --------------------------------------------------------------------
TycoonConfig.PlotCount = 6 -- set the place's Max Players to match this
TycoonConfig.PlotSpacing = 160
TycoonConfig.PlotSize = Vector3.new(120, 1, 120)
TycoonConfig.SpawnOffset = Vector3.new(0, 3, 45)

-- Production line ----------------------------------------------------------
TycoonConfig.Layout = {
	ConveyorZ = -30,
	ConveyorStartX = -45,
	ConveyorEndX = 40,
	ConveyorWidth = 6,
	ButtonRowZ = 20,
	ButtonStartX = -42,
	ButtonSpacing = 12,
}
TycoonConfig.ConveyorSpeed = 12 -- studs per second
TycoonConfig.MaxDropsPerPlot = 80
TycoonConfig.DropLifetime = 30 -- seconds before an uncollected drop is removed

--[[
	Purchasable items, in the order their buttons appear.

	Common fields:
		Id        unique string (this is what gets saved - don't rename it!)
		Name      shown on the button
		Price     cost in cash
		Requires  Id of the item that must be owned before this button appears
		Kind      "Dropper" | "Upgrader" | "Decor"

	Dropper:  X, DropValue, DropInterval, Color, DropColor
	Upgrader: X, Multiplier, Color
	Decor:    Parts = { { Size, Offset, Color, Material } }
]]
TycoonConfig.Items = {
	{
		Id = "Dropper1",
		Name = "Basic Dropper",
		Price = 0,
		Kind = "Dropper",
		X = -38,
		DropValue = 1,
		DropInterval = 2,
		Color = Color3.fromRGB(163, 162, 165),
		DropColor = Color3.fromRGB(124, 92, 70),
	},
	{
		Id = "Dropper2",
		Name = "Stone Dropper",
		Price = 25,
		Requires = "Dropper1",
		Kind = "Dropper",
		X = -28,
		DropValue = 2,
		DropInterval = 2,
		Color = Color3.fromRGB(99, 95, 98),
		DropColor = Color3.fromRGB(140, 140, 140),
	},
	{
		Id = "Walls",
		Name = "Walls",
		Price = 100,
		Requires = "Dropper2",
		Kind = "Decor",
		Parts = {
			{ Size = Vector3.new(120, 12, 1), Offset = Vector3.new(0, 6, -59.5) },
			{ Size = Vector3.new(1, 12, 120), Offset = Vector3.new(-59.5, 6, 0) },
			{ Size = Vector3.new(1, 12, 120), Offset = Vector3.new(59.5, 6, 0) },
		},
		Color = Color3.fromRGB(196, 140, 98),
		Material = Enum.Material.Brick,
	},
	{
		Id = "Upgrader1",
		Name = "Polisher (x2)",
		Price = 250,
		Requires = "Dropper2",
		Kind = "Upgrader",
		X = 18,
		Multiplier = 2,
		Color = Color3.fromRGB(0, 170, 255),
	},
	{
		Id = "Dropper3",
		Name = "Iron Dropper",
		Price = 600,
		Requires = "Upgrader1",
		Kind = "Dropper",
		X = -18,
		DropValue = 5,
		DropInterval = 1.5,
		Color = Color3.fromRGB(205, 205, 210),
		DropColor = Color3.fromRGB(230, 230, 235),
	},
	{
		Id = "Dropper4",
		Name = "Gold Dropper",
		Price = 2000,
		Requires = "Dropper3",
		Kind = "Dropper",
		X = -8,
		DropValue = 15,
		DropInterval = 1.5,
		Color = Color3.fromRGB(239, 184, 56),
		DropColor = Color3.fromRGB(255, 215, 0),
	},
	{
		Id = "Upgrader2",
		Name = "Refinery (x3)",
		Price = 5000,
		Requires = "Dropper4",
		Kind = "Upgrader",
		X = 28,
		Multiplier = 3,
		Color = Color3.fromRGB(255, 85, 255),
	},
	{
		Id = "Dropper5",
		Name = "Diamond Dropper",
		Price = 12000,
		Requires = "Upgrader2",
		Kind = "Dropper",
		X = 2,
		DropValue = 50,
		DropInterval = 1,
		Color = Color3.fromRGB(85, 255, 255),
		DropColor = Color3.fromRGB(170, 255, 255),
	},
}


--============================================================================
-- FORMAT
--============================================================================

local Format = {}

local SUFFIXES = { "", "K", "M", "B", "T", "Qd", "Qn" }

function Format.number(n: number): string
	n = math.floor(n)
	if math.abs(n) < 1000 then
		return tostring(n)
	end

	local value = n
	local index = 1
	while math.abs(value) >= 1000 and index < #SUFFIXES do
		value /= 1000
		index += 1
	end

	-- "1.0K" -> "1K"
	local text = string.format("%.1f%s", value, SUFFIXES[index])
	return (text:gsub("%.0(%a)", "%1"))
end

function Format.cash(n: number): string
	return "$" .. Format.number(n)
end


--============================================================================
-- DATA (saving + leaderstats)
--============================================================================

local DataService = {}

local MAX_RETRIES = 3

local store: DataStore? = nil
-- [Player] = { Data = table, CanSave = boolean }
local sessions = {}

local function keyFor(player: Player): string
	return "Player_" .. player.UserId
end

local function defaultData()
	return {
		Cash = TycoonConfig.StartingCash,
		Owned = {},
	}
end

-- Fill in any missing fields so old saves keep working after updates.
local function reconcile(data)
	if typeof(data) ~= "table" then
		return defaultData()
	end
	if typeof(data.Cash) ~= "number" then
		data.Cash = TycoonConfig.StartingCash
	end
	if typeof(data.Owned) ~= "table" then
		data.Owned = {}
	end
	return data
end

local function withRetries(label: string, fn: () -> any): (boolean, any)
	for attempt = 1, MAX_RETRIES do
		local ok, result = pcall(fn)
		if ok then
			return true, result
		end
		warn(("[DataService] %s failed (attempt %d/%d): %s"):format(label, attempt, MAX_RETRIES, tostring(result)))
		if attempt < MAX_RETRIES then
			task.wait(2 ^ attempt)
		end
	end
	return false, nil
end

local function updateLeaderstat(player: Player, cash: number)
	local leaderstats = player:FindFirstChild("leaderstats")
	local cashValue = leaderstats and leaderstats:FindFirstChild("Cash")
	if cashValue then
		cashValue.Value = cash
	end
end

-- Lifecycle -----------------------------------------------------------------

function DataService.Init()
	local ok, result = pcall(function()
		return DataStoreService:GetDataStore(TycoonConfig.DataStoreName)
	end)
	if ok then
		store = result
	else
		warn("[DataService] DataStores unavailable, progress will NOT save: " .. tostring(result))
	end

	-- Autosave loop
	task.spawn(function()
		while true do
			task.wait(TycoonConfig.AutosaveInterval)
			for player in sessions do
				task.spawn(DataService.Save, player)
			end
		end
	end)

	-- Save everyone when the server shuts down
	game:BindToClose(function()
		local pending = 0
		for player in sessions do
			pending += 1
			task.spawn(function()
				DataService.Save(player)
				pending -= 1
			end)
		end
		local deadline = os.clock() + 25
		while pending > 0 and os.clock() < deadline do
			task.wait(0.1)
		end
	end)
end

-- Returns the player's data, or nil if they left while it was loading.
function DataService.Load(player: Player)
	local data = nil
	local canSave = false

	if store then
		local ok, result = withRetries("Load " .. player.Name, function()
			return store:GetAsync(keyFor(player))
		end)
		if ok then
			data = reconcile(result) -- result is nil for brand new players
			canSave = true
		end
	end

	if not data then
		-- Never save temporary data: it would overwrite the real save.
		warn(("[DataService] Using temporary data for %s; it will not be saved."):format(player.Name))
		data = defaultData()
	end

	if not player.Parent then
		return nil
	end

	sessions[player] = { Data = data, CanSave = canSave }
	return data
end

function DataService.Save(player: Player): boolean
	local session = sessions[player]
	if not session or not session.CanSave or not store then
		return false
	end

	local snapshot = {
		Cash = session.Data.Cash,
		Owned = table.clone(session.Data.Owned),
	}

	local ok = withRetries("Save " .. player.Name, function()
		store:UpdateAsync(keyFor(player), function()
			return snapshot
		end)
	end)
	return ok
end

-- Call when the player leaves.
function DataService.Release(player: Player)
	if not sessions[player] then
		return
	end
	DataService.Save(player)
	sessions[player] = nil
end

function DataService.CreateLeaderstats(player: Player)
	local session = sessions[player]
	if not session then
		return
	end

	local leaderstats = Instance.new("Folder")
	leaderstats.Name = "leaderstats"

	local cash = Instance.new("IntValue")
	cash.Name = "Cash"
	cash.Value = session.Data.Cash
	cash.Parent = leaderstats

	leaderstats.Parent = player
end

-- Cash ------------------------------------------------------------------------

function DataService.GetCash(player: Player): number
	local session = sessions[player]
	return session and session.Data.Cash or 0
end

function DataService.AddCash(player: Player, amount: number)
	local session = sessions[player]
	if not session then
		return
	end
	session.Data.Cash += math.floor(amount)
	updateLeaderstat(player, session.Data.Cash)
end

-- Removes the cash and returns true if the player can afford it.
function DataService.TrySpend(player: Player, amount: number): boolean
	local session = sessions[player]
	if not session or session.Data.Cash < amount then
		return false
	end
	session.Data.Cash -= amount
	updateLeaderstat(player, session.Data.Cash)
	return true
end

-- Ownership -----------------------------------------------------------------

function DataService.Owns(player: Player, itemId: string): boolean
	local session = sessions[player]
	return session ~= nil and session.Data.Owned[itemId] == true
end

function DataService.SetOwned(player: Player, itemId: string)
	local session = sessions[player]
	if session then
		session.Data.Owned[itemId] = true
	end
end


--============================================================================
-- TYCOON (plots, droppers, conveyor, upgraders, collector, buttons)
--============================================================================

local TycoonService = {}

local Layout = TycoonConfig.Layout

local plots = {}
local plotByPlayer: { [Player]: any } = {}
local itemsById = {}
local notifyRemote: RemoteEvent

for _, item in TycoonConfig.Items do
	assert(itemsById[item.Id] == nil, "Duplicate tycoon item Id: " .. item.Id)
	itemsById[item.Id] = item
end

-- Helpers ---------------------------------------------------------------------

local function makePart(parent: Instance, props): Part
	local part = Instance.new("Part")
	part.Anchored = true
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	for key, value in props do
		part[key] = value
	end
	part.Parent = parent
	return part
end

-- CFrame of a point relative to the plot's floor centre.
local function at(plot, x: number, y: number, z: number): CFrame
	return plot.CFrame * CFrame.new(x, y, z)
end

local function notify(player: Player, message: string, kind: string?)
	notifyRemote:FireClient(player, message, kind or "Info")
end

local function addLabel(parent: Instance, text: string): TextLabel
	local label = Instance.new("TextLabel")
	label.Size = UDim2.fromScale(1, 1)
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

local function spawnDrop(plot, item, spawnCFrame: CFrame)
	if #plot.Drops:GetChildren() >= TycoonConfig.MaxDropsPerPlot then
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
	drop:SetAttribute("Value", item.DropValue)

	-- Keep drop physics on the server so clients can't fling them around.
	pcall(function()
		drop:SetNetworkOwner(nil)
	end)

	Debris:AddItem(drop, TycoonConfig.DropLifetime)
end

-- Item builders ---------------------------------------------------------------

local builders = {}

function builders.Dropper(plot, item, model: Model)
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

function builders.Upgrader(plot, item, model: Model)
	local z = Layout.ConveyorZ
	local x = item.X
	local frameColor = Color3.fromRGB(45, 45, 45)

	for _, side in { -1, 1 } do
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

	local flag = "Upgraded_" .. item.Id
	field.Touched:Connect(function(hit)
		if hit.Parent ~= plot.Drops or hit:GetAttribute(flag) then
			return
		end
		hit:SetAttribute(flag, true)
		hit:SetAttribute("Value", (hit:GetAttribute("Value") or 0) * item.Multiplier)
		hit.Color = item.Color
		hit.Material = Enum.Material.Neon
	end)
end

function builders.Decor(plot, item, model: Model)
	for index, spec in item.Parts do
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

local function createButton(plot, item, index: number): BasePart
	local x = Layout.ButtonStartX + (index - 1) * Layout.ButtonSpacing
	local button = makePart(plot.ButtonFolder, {
		Name = item.Id .. "Button",
		Size = Vector3.new(5, 1, 5),
		CFrame = at(plot, x, 0.5, Layout.ButtonRowZ),
		Color = Color3.fromRGB(0, 200, 90),
		Material = Enum.Material.Neon,
	})

	local billboard = Instance.new("BillboardGui")
	billboard.Size = UDim2.fromScale(7, 2.5)
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
	for index, item in TycoonConfig.Items do
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

local function buildPlot(parent: Instance, index: number)
	local offsetX = (index - 1 - (TycoonConfig.PlotCount - 1) / 2) * TycoonConfig.PlotSpacing
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
		Size = TycoonConfig.PlotSize,
		CFrame = at(plot, 0, -TycoonConfig.PlotSize.Y / 2, 0),
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
	conveyor.AssemblyLinearVelocity = plot.CFrame.RightVector * TycoonConfig.ConveyorSpeed

	local halfWidth = Layout.ConveyorWidth / 2
	for _, side in { -1, 1 } do
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
		if hit.Parent ~= plot.Drops or hit:GetAttribute("Collected") then
			return
		end
		hit:SetAttribute("Collected", true)
		local owner = plot.Owner
		if owner then
			DataService.AddCash(owner, hit:GetAttribute("Value") or 0)
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
	for _, face in { Enum.NormalId.Front, Enum.NormalId.Back } do
		local surface = Instance.new("SurfaceGui")
		surface.Face = face
		surface.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
		surface.PixelsPerStud = 25
		surface.Parent = sign
		table.insert(signLabels, addLabel(surface, ""))
	end
	plot.SignLabels = signLabels

	local function folder(name: string): Folder
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

local function setSignText(plot, text: string)
	for _, label in plot.SignLabels do
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

	for index = 1, TycoonConfig.PlotCount do
		local plot = buildPlot(container, index)
		setSignText(plot, "Unclaimed")
		plots[index] = plot
	end
end

function TycoonService.AssignPlot(player: Player)
	if plotByPlayer[player] then
		return plotByPlayer[player]
	end

	local plot = nil
	for _, candidate in plots do
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
	plot.Session += 1
	plotByPlayer[player] = plot
	setSignText(plot, player.DisplayName .. "'s Tycoon")

	-- Rebuild everything the player already owns.
	for _, item in TycoonConfig.Items do
		if DataService.Owns(player, item.Id) then
			buildItem(plot, item)
		end
	end
	refreshButtons(plot)

	-- Spawn the player at their plot.
	local spawnPosition = at(plot, TycoonConfig.SpawnOffset.X, TycoonConfig.SpawnOffset.Y, TycoonConfig.SpawnOffset.Z).Position
	-- Face toward the back of the plot (the production line).
	local spawnCFrame = CFrame.lookAt(spawnPosition, spawnPosition + plot.CFrame.LookVector)
	local function onCharacter(character: Model)
		local root = character:WaitForChild("HumanoidRootPart", 10)
		if not root or plot.Owner ~= player then
			return
		end
		task.wait() -- let the default spawn placement finish first
		character:PivotTo(spawnCFrame)
	end
	plot.CharacterConn = player.CharacterAdded:Connect(onCharacter)
	if player.Character then
		task.spawn(onCharacter, player.Character)
	end

	notify(player, "Welcome to your tycoon!", "Success")
	return plot
end

function TycoonService.ReleasePlot(player: Player)
	local plot = plotByPlayer[player]
	if not plot then
		return
	end
	plotByPlayer[player] = nil

	plot.Session += 1 -- stops dropper loops
	plot.Owner = nil
	if plot.CharacterConn then
		plot.CharacterConn:Disconnect()
		plot.CharacterConn = nil
	end

	plot.Items:ClearAllChildren()
	plot.ButtonFolder:ClearAllChildren()
	plot.Drops:ClearAllChildren()
	table.clear(plot.Buttons)
	setSignText(plot, "Unclaimed")
end

function TycoonService.TryPurchase(player: Player, itemId: string): boolean
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


--============================================================================
-- START
--============================================================================

DataService.Init()
TycoonService.Init()

local function onPlayerAdded(player: Player)
	local data = DataService.Load(player)
	if not data or not player.Parent then
		return -- left while loading
	end

	DataService.CreateLeaderstats(player)
	TycoonService.AssignPlot(player)
end

local function onPlayerRemoving(player: Player)
	TycoonService.ReleasePlot(player)
	DataService.Release(player)
end

Players.PlayerAdded:Connect(onPlayerAdded)
Players.PlayerRemoving:Connect(onPlayerRemoving)

-- Players who joined before this script ran (common in Studio play tests).
for _, player in Players:GetPlayers() do
	task.spawn(onPlayerAdded, player)
end
