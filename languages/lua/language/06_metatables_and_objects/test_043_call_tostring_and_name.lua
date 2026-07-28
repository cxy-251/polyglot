-- polyglot-covers: lua.metatables.call_tostring_and_name

local t = require("support.assertions")

local value = setmetatable({base = 40}, {
    __call = function(self, increment)
        return self.base + increment
    end,
    __tostring = function(self)
        return "Counter(" .. self.base .. ")"
    end,
    __name = "Counter",
})

t.equal(value(2), 42)
t.equal(tostring(value), "Counter(40)")

local ok, message = pcall(function()
    return value + true
end)
t.falsey(ok)
t.matches(message, "Counter")

t.done()
