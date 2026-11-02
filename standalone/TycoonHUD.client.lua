--[[
	TYCOON - CLIENT HUD (all-in-one, plain Lua 5.1 compatible)
	Put this in: StarterPlayer > StarterPlayerScripts  (as a LocalScript)
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

local Format = {}

local SUFFIXES = { "", "K", "M", "B", "T", "Qd", "Qn" }

function Format.number(n)
	n = math.floor(n)
	if math.abs(n) < 1000 then
		return tostring(n)
	end

	local value = n
	local index = 1
	while math.abs(value) >= 1000 and index < #SUFFIXES do
		value = value / 1000
		index = index + 1
	end

	-- "1.0K" -> "1K"
	local text = string.format("%.1f%s", value, SUFFIXES[index])
	return (text:gsub("%.0(%a)", "%1"))
end

function Format.cash(n)
	return "$" .. Format.number(n)
end


local player = Players.LocalPlayer
local notifyRemote = ReplicatedStorage:WaitForChild("TycoonRemotes"):WaitForChild("Notify")

local NOTIFY_COLORS = {
	Info = Color3.fromRGB(40, 40, 40),
	Success = Color3.fromRGB(30, 140, 70),
	Error = Color3.fromRGB(170, 40, 40),
}

-- GUI -------------------------------------------------------------------------

local gui = Instance.new("ScreenGui")
gui.Name = "TycoonHUD"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = false

local cashFrame = Instance.new("Frame")
cashFrame.AnchorPoint = Vector2.new(0.5, 0)
cashFrame.Position = UDim2.new(0.5, 0, 0, 10)
cashFrame.Size = UDim2.new(0, 220, 0, 50)
cashFrame.BackgroundColor3 = Color3.fromRGB(25, 25, 25)
cashFrame.BackgroundTransparency = 0.2
cashFrame.Parent = gui
Instance.new("UICorner", cashFrame).CornerRadius = UDim.new(0, 12)

local cashLabel = Instance.new("TextLabel")
cashLabel.Size = UDim2.new(1, 0, 1, 0)
cashLabel.BackgroundTransparency = 1
cashLabel.Font = Enum.Font.FredokaOne
cashLabel.TextScaled = true
cashLabel.TextColor3 = Color3.fromRGB(120, 255, 120)
cashLabel.Text = "$0"
cashLabel.Parent = cashFrame
local padding = Instance.new("UIPadding")
padding.PaddingTop = UDim.new(0, 6)
padding.PaddingBottom = UDim.new(0, 6)
padding.Parent = cashLabel

local toastList = Instance.new("Frame")
toastList.AnchorPoint = Vector2.new(0.5, 1)
toastList.Position = UDim2.new(0.5, 0, 1, -20)
toastList.Size = UDim2.new(0, 360, 0, 200)
toastList.BackgroundTransparency = 1
toastList.Parent = gui
local layout = Instance.new("UIListLayout")
layout.VerticalAlignment = Enum.VerticalAlignment.Bottom
layout.HorizontalAlignment = Enum.HorizontalAlignment.Center
layout.SortOrder = Enum.SortOrder.LayoutOrder
layout.Padding = UDim.new(0, 6)
layout.Parent = toastList

gui.Parent = player:WaitForChild("PlayerGui")

-- Cash display ----------------------------------------------------------------

local function bindCash(cashValue)
	local function update()
		cashLabel.Text = Format.cash(cashValue.Value)
		cashFrame.Size = UDim2.new(0, 240, 0, 56)
		TweenService:Create(cashFrame, TweenInfo.new(0.15), { Size = UDim2.new(0, 220, 0, 50) }):Play()
	end
	cashValue.Changed:Connect(update)
	update()
end

task.spawn(function()
	-- Passing a timeout avoids the "infinite yield" warning while data loads.
	local leaderstats = player:WaitForChild("leaderstats", math.huge)
	bindCash(leaderstats:WaitForChild("Cash", math.huge))
end)

-- Notifications -----------------------------------------------------------------

local toastCount = 0

local function showToast(message, kind)
	toastCount = toastCount + 1

	local toast = Instance.new("TextLabel")
	toast.LayoutOrder = toastCount
	toast.Size = UDim2.new(0, 360, 0, 40)
	toast.BackgroundColor3 = NOTIFY_COLORS[kind] or NOTIFY_COLORS.Info
	toast.BackgroundTransparency = 1
	toast.TextTransparency = 1
	toast.Font = Enum.Font.GothamBold
	toast.TextSize = 18
	toast.TextColor3 = Color3.new(1, 1, 1)
	toast.Text = message
	toast.Parent = toastList
	Instance.new("UICorner", toast).CornerRadius = UDim.new(0, 10)

	local fadeIn = TweenInfo.new(0.2)
	TweenService:Create(toast, fadeIn, { BackgroundTransparency = 0.15, TextTransparency = 0 }):Play()

	task.delay(3, function()
		local fadeOut = TweenService:Create(toast, TweenInfo.new(0.4), { BackgroundTransparency = 1, TextTransparency = 1 })
		fadeOut:Play()
		fadeOut.Completed:Wait()
		toast:Destroy()
	end)
end

notifyRemote.OnClientEvent:Connect(showToast)
