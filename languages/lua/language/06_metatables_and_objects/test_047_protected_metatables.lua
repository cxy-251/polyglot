-- polyglot-covers: lua.metatables.protected_metatables

local t = require("support.assertions")

local actual_metatable = {
    __index = {answer = 42},
    __metatable = "locked",
}
local value = setmetatable({}, actual_metatable)

t.equal(getmetatable(value), "locked")
t.equal(value.answer, 42)
t.raises(function()
    setmetatable(value, {})
end, "protected metatable")

-- debug 库具有更强权限，可以绕过普通 getmetatable/setmetatable 封装。
t.same(debug.getmetatable(value), actual_metatable)
debug.setmetatable(value, nil)
t.equal(getmetatable(value), nil)

t.done()
