-- polyglot-covers: lua.metatables.call_name_tostring_and_protection

local t = require("support.assertions")

local actual_metatable = {
    __call = function(self, increment)
        return self.base + increment
    end,
    __tostring = function(self)
        return "Counter(" .. self.base .. ")"
    end,
    __name = "Counter",
    __metatable = "locked",
}
local value = setmetatable({base = 40}, actual_metatable)
t.equal(value(2), 42)
t.equal(tostring(value), "Counter(40)")
t.equal(getmetatable(value), "locked")
t.raises(function() setmetatable(value, {}) end)

local ok, message = pcall(function() return value + true end)
t.falsey(ok)
t.matches(message, "Counter")

-- debug 库刻意绕过普通保护；它是诊断权限边界，不是对象封装的后门设计模式。
t.same(debug.getmetatable(value), actual_metatable)
debug.setmetatable(value, nil)
t.equal(getmetatable(value), nil)

t.done()
