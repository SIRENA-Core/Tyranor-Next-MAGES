-- Load one game profile the way the engine does (src/profile/profile.cpp: `root`, `include`, `getPatchProfile`, the
-- enums of DefineEnum) and print the resulting `root` table as sorted "path = value" lines.
-- usage: luarun snapshot.lua <patched checkout> <profile id>
-- Enum values are not known outside the engine; they print as "Type.Name" ("A|B" for values combined with `|`).
local checkout, id = arg[1], arg[2]

local function words(s)
    local set = {}
    for w in string.gmatch(tostring(s), "[^|]+") do set[w] = true end
    return set
end
local function combine(a, b)
    local set = words(a)
    for w in pairs(words(b)) do set[w] = true end
    local list = {}
    for w in pairs(set) do list[#list + 1] = w end
    table.sort(list)
    return table.concat(list, "|")
end
getmetatable("").__bor = combine

setmetatable(_G, {
    __index = function(_, name)
        if type(name) == "string" and name:match("^%u") then
            local enum = setmetatable({}, { __index = function(_, value) return name .. "." .. value end })
            rawset(_G, name, enum)
            return enum
        end
    end,
})

print = function() end
include = function(path) dofile(path) end
getPatchProfile = function() return "" end

root = {}
root.BasePaths = {
    RootProfilesDir = checkout .. "/profiles",
    RootGamedataDir = "<gamedata>",
    RootSavesDir = "<saves>",
    RootPatchesDir = "<patches>",
}
include(checkout .. "/gamedefinitions.lua")
local definition = root.GameDefinitions[id]
assert(definition, "no game definition " .. tostring(id))
root.GameDefinitions = nil
include(definition.GameProfile)
root.BasePaths = nil

local out = {}
local function value(v)
    if type(v) == "string" then
        local s, e = v:find(checkout, 1, true)
        if s then v = v:sub(1, s - 1) .. "<checkout>" .. v:sub(e + 1) end
        return string.format("%q", v)
    elseif math.type(v) == "float" then
        return string.format("%.17g", v)
    end
    return tostring(v)
end
local function keyorder(a, b)
    local ta, tb = type(a), type(b)
    if ta ~= tb then return ta < tb end
    if ta == "number" or ta == "string" then return a < b end
    return tostring(a) < tostring(b)
end
local seen = {}
local function walk(t, path)
    if seen[t] then
        out[#out + 1] = path .. " = <same as " .. seen[t] .. ">"
        return
    end
    seen[t] = path
    local keys = {}
    for k in pairs(t) do keys[#keys + 1] = k end
    table.sort(keys, keyorder)
    if #keys == 0 then out[#out + 1] = path .. " = {}" end
    for _, k in ipairs(keys) do
        local p = type(k) == "string" and (path == "" and k or path .. "." .. k) or path .. "[" .. tostring(k) .. "]"
        local v = t[k]
        if type(v) == "table" then
            walk(v, p)
        elseif type(v) == "function" then
            out[#out + 1] = p .. " = <function>"
        else
            out[#out + 1] = p .. " = " .. value(v)
        end
    end
end
walk(root, "")
io.write(table.concat(out, "\n"), "\n")
