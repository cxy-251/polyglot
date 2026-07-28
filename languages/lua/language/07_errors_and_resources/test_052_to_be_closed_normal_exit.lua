-- polyglot-covers: lua.resources.to_be_closed_normal_exit

local t = require("support.assertions")
local events = {}

local metatable = {
    __close = function(self, error_value)
        events[#events + 1] = {self.name, error_value}
    end,
}

do
    local first <close> = setmetatable({name = "first"}, metatable)
    local second <close> = setmetatable({name = "second"}, metatable)
    t.equal(first.name, "first")
    t.equal(second.name, "second")
end

t.equal(#events, 2)
t.equal(events[1][1], "second")
t.equal(events[2][1], "first")
t.equal(events[1][2], nil)
t.equal(events[2][2], nil)

t.done()
