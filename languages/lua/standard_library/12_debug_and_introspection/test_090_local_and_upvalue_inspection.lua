-- polyglot-covers: lua.debug.locals_and_upvalues

local t = require("support.assertions")

local captured = "upvalue"
local function inspect(argument)
    local local_value = 42
    local locals = {}
    local index = 1
    while true do
        local name, value = debug.getlocal(1, index)
        if name == nil then
            break
        end
        locals[name] = value
        index = index + 1
    end
    return locals.argument, locals.local_value, captured
end

local argument, local_value, upvalue = inspect("parameter")
t.equal(argument, "parameter")
t.equal(local_value, 42)
t.equal(upvalue, "upvalue")

local upvalues = {}
local upvalue_index = 1
while true do
    local name, value = debug.getupvalue(inspect, upvalue_index)
    if name == nil then
        break
    end
    upvalues[name] = value
    upvalue_index = upvalue_index + 1
end
t.same(upvalues._ENV, _ENV)
t.equal(upvalues.captured, "upvalue")

t.done()
