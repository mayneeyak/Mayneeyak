--[[
	CHARACTER MOVES - CLIENT PANEL  (plain Lua 5.1, works in Studio Lite)
	Put this in: StarterPlayer > StarterPlayerScripts  (as a LocalScript)

	Shows a "Moves" panel. Tap a move to make your character do it,
	"Play Series" to do every move in a row, or "Stop" to stop.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local player = Players.LocalPlayer
local remotes = ReplicatedStorage:WaitForChild("CharacterMoves")
local playRemote = remotes:WaitForChild("PlayMove")
local moveList = remotes:WaitForChild("MoveList")

local BUTTON_HEIGHT = 40
local PANEL_WIDTH = 170

-- GUI -------------------------------------------------------------------------

local gui = Instance.new("ScreenGui")
gui.Name = "CharacterMovesPanel"
gui.ResetOnSpawn = false

-- Top-right, away from the mobile joystick and jump button.
local toggle = Instance.new("TextButton")
toggle.AnchorPoint = Vector2.new(1, 0)
toggle.Position = UDim2.new(1, -10, 0, 10)
toggle.Size = UDim2.new(0, PANEL_WIDTH, 0, BUTTON_HEIGHT)
toggle.BackgroundColor3 = Color3.fromRGB(120, 60, 200)
toggle.TextColor3 = Color3.new(1, 1, 1)
toggle.Font = Enum.Font.GothamBold
toggle.TextSize = 20
toggle.Text = "Moves  [-]"
toggle.Parent = gui
Instance.new("UICorner", toggle).CornerRadius = UDim.new(0, 10)

local panel = Instance.new("ScrollingFrame")
panel.AnchorPoint = Vector2.new(1, 0)
panel.Position = UDim2.new(1, -10, 0, 10 + BUTTON_HEIGHT + 6)
panel.Size = UDim2.new(0, PANEL_WIDTH, 0.55, 0)
panel.BackgroundColor3 = Color3.fromRGB(25, 25, 35)
panel.BackgroundTransparency = 0.25
panel.BorderSizePixel = 0
panel.ScrollBarThickness = 6
panel.Parent = gui
Instance.new("UICorner", panel).CornerRadius = UDim.new(0, 10)

local padding = Instance.new("UIPadding")
padding.PaddingTop = UDim.new(0, 6)
padding.PaddingBottom = UDim.new(0, 6)
padding.PaddingLeft = UDim.new(0, 6)
padding.PaddingRight = UDim.new(0, 10)
padding.Parent = panel

local layout = Instance.new("UIListLayout")
layout.SortOrder = Enum.SortOrder.LayoutOrder
layout.Padding = UDim.new(0, 6)
layout.Parent = panel

local buttonCount = 0

local function addButton(text, color, onClick)
	buttonCount = buttonCount + 1

	local button = Instance.new("TextButton")
	button.LayoutOrder = buttonCount
	button.Size = UDim2.new(1, 0, 0, BUTTON_HEIGHT)
	button.BackgroundColor3 = color
	button.TextColor3 = Color3.new(1, 1, 1)
	button.Font = Enum.Font.GothamBold
	button.TextSize = 18
	button.Text = text
	button.Parent = panel
	Instance.new("UICorner", button).CornerRadius = UDim.new(0, 8)

	button.MouseButton1Click:Connect(onClick)

	-- Set the scroll area by hand (works in older editors too).
	panel.CanvasSize = UDim2.new(0, 0, 0, buttonCount * (BUTTON_HEIGHT + 6) + 12)
	return button
end

addButton("Play Series", Color3.fromRGB(30, 150, 80), function()
	playRemote:FireServer("Series")
end)

addButton("Stop", Color3.fromRGB(170, 40, 40), function()
	playRemote:FireServer("Stop")
end)

-- One button per move, in the server's order.
local entries = moveList:GetChildren()
table.sort(entries, function(a, b)
	return a.Name < b.Name
end)
for _, entry in ipairs(entries) do
	local moveName = entry.Value
	addButton(moveName, Color3.fromRGB(60, 60, 80), function()
		playRemote:FireServer("Move", moveName)
	end)
end

toggle.MouseButton1Click:Connect(function()
	panel.Visible = not panel.Visible
	toggle.Text = panel.Visible and "Moves  [-]" or "Moves  [+]"
end)

gui.Parent = player:WaitForChild("PlayerGui")
