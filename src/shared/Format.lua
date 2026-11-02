--[[
	Format
	Number helpers shared by server billboards and the client HUD.
	Format.number(1530) --> "1.5K"
	Format.cash(1530)   --> "$1.5K"
]]

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

return Format
