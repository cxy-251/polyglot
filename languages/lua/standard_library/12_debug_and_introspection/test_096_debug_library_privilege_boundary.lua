-- polyglot-covers: lua.debug.privilege_boundary

local t = require("support.assertions")
local secret = "hidden"
local function accessor()
    return secret
end

t.equal(accessor(), "hidden")
local name, value = debug.getupvalue(accessor, 1)
t.equal(name, "secret")
t.equal(value, "hidden")
t.equal(debug.setupvalue(accessor, 1, "revealed"), "secret")
t.equal(accessor(), "revealed")

local info = debug.getinfo(accessor, "f")
t.same(info.func, accessor)

-- debug 可读取并改写封闭状态，属于强权限诊断接口，不是普通封装设计模式。
t.done()
