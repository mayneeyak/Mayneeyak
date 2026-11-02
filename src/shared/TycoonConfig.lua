--[[
	TycoonConfig
	All tunable numbers for the tycoon live here. Shared so the client can
	read prices/names too.

	Coordinates are in studs, relative to the centre of a plot's floor
	surface (Y = 0 is the top of the floor). +X runs along the conveyor
	toward the collector, -Z is the back of the plot.
]]

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

return TycoonConfig
