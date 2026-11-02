--[[
	DataService
	Loads, caches and saves each player's tycoon data:
		{ Cash = number, Owned = { [itemId] = true } }

	Also owns the "leaderstats" Cash value so the server has one place
	where cash changes.
]]

local DataStoreService = game:GetService("DataStoreService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.TycoonConfig)

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
		Cash = Config.StartingCash,
		Owned = {},
	}
end

-- Fill in any missing fields so old saves keep working after updates.
local function reconcile(data)
	if typeof(data) ~= "table" then
		return defaultData()
	end
	if typeof(data.Cash) ~= "number" then
		data.Cash = Config.StartingCash
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
		return DataStoreService:GetDataStore(Config.DataStoreName)
	end)
	if ok then
		store = result
	else
		warn("[DataService] DataStores unavailable, progress will NOT save: " .. tostring(result))
	end

	-- Autosave loop
	task.spawn(function()
		while true do
			task.wait(Config.AutosaveInterval)
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

return DataService
