-- polyglot-covers: lua.functions.multires_list_positions

local t = require("support.assertions")

local function pair()
    return "left", "right"
end

local function capture(...)
    return table.pack(...)
end

t.pack_equal(capture(pair()), {n = 2, "left", "right"})
t.pack_equal(capture(pair(), "tail"), {n = 2, "left", "tail"})
t.pack_equal(capture("head", pair()), {n = 3, "head", "left", "right"})

local constructor = {pair(), "tail"}
t.equal(#constructor, 2)
t.equal(constructor[1], "left")
t.equal(constructor[2], "tail")

t.done()
