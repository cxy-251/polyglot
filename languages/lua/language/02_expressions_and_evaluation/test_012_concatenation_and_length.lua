-- polyglot-covers: lua.expressions.concatenation_and_length

local t = require("support.assertions")

t.equal("Lua" .. 5.5, "Lua5.5")
t.equal(#"Lua\0", 4)
t.equal(#{10, 20, 30}, 3)

local events = {}
local value = setmetatable({}, {
    __concat = function(left, right)
        events[#events + 1] = {left, right}
        return "joined"
    end,
    __len = function()
        return 99
    end,
})

t.equal(value .. "x", "joined")
t.equal(#value, 99)
t.equal(#events, 1)
t.same(events[1][1], value)

t.done()
