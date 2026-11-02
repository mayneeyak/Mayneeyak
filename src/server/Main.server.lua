--[[
	Main (Script)
	Server entry point: starts the services and wires up players.
]]

local Players = game:GetService("Players")

local Services = script.Parent.Services
local DataService = require(Services.DataService)
local TycoonService = require(Services.TycoonService)

DataService.Init()
TycoonService.Init()

local function onPlayerAdded(player)
	local data = DataService.Load(player)
	if not data or not player.Parent then
		return -- left while loading
	end

	DataService.CreateLeaderstats(player)
	TycoonService.AssignPlot(player)
end

local function onPlayerRemoving(player)
	TycoonService.ReleasePlot(player)
	DataService.Release(player)
end

Players.PlayerAdded:Connect(onPlayerAdded)
Players.PlayerRemoving:Connect(onPlayerRemoving)

-- Players who joined before this script ran (common in Studio play tests).
for _, player in ipairs(Players:GetPlayers()) do
	task.spawn(onPlayerAdded, player)
end
