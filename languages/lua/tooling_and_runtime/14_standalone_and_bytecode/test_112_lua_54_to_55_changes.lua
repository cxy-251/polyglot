-- polyglot-covers: lua.runtime.lua_54_to_55_changes

local t = require("support.assertions")

local environment = {}
local global_chunk = assert(load(
    "global answer = 42; return answer",
    "global-declaration",
    "t",
    environment
))
t.equal(global_chunk(), 42)
t.equal(environment.answer, 42)
t.equal(select(1, load("for i = 1, 1 do i = 2 end", "readonly-loop", "t")), nil)

local named_vararg = assert(load([[
    return function(... args)
        return args.n, args[1], args[2]
    end
]], "named-vararg", "t"))()
t.pack_equal(table.pack(named_vararg("a", "b")), {n = 3, 2, "a", "b"})

t.equal(type(table.create), "function")
local position, final_position = utf8.offset("中", 1)
t.equal(position, 1)
t.equal(final_position, 3)

local pause = collectgarbage("param", "pause")
t.equal(type(pause), "number")

-- 5.5 的 C API 还改变 lua_newstate、lua_dump 与 GC 参数入口，后续 C API 课程单独验证。
t.done()
