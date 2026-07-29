-- polyglot-covers: lua.debug.function_local_and_upvalue_information

local t = require("support.assertions")
local captured = "upvalue"
local function sample(argument, ...)
    local local_value = 42
    local locals = {}
    local index = 1
    while true do
        local name, value = debug.getlocal(1, index)
        if name == nil then break end
        locals[name] = value
        index = index + 1
    end
    return locals.argument, locals.local_value, captured, select("#", ...)
end

local info = debug.getinfo(sample, "Snu")
t.equal(info.what, "Lua")
t.equal(info.nparams, 1)
t.truth(info.isvararg)
t.equal(type(info.linedefined), "number")
t.equal(debug.getinfo(math.abs, "S").what, "C")

local argument, local_value, upvalue, vararg_count = sample("parameter", "extra")
t.equal(argument, "parameter")
t.equal(local_value, 42)
t.equal(upvalue, "upvalue")
t.equal(vararg_count, 1)

local observed = {}
for index = 1, 10 do
    local name, value = debug.getupvalue(sample, index)
    if name == nil then break end
    observed[name] = value
end
t.equal(observed.captured, "upvalue")
t.same(observed._ENV, _ENV)

-- 行号和 short_src 是诊断观察，不用于锁定仓库文件名或源码布局。
t.done()
