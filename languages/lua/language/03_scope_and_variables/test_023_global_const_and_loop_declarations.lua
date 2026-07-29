-- polyglot-covers: lua.scope.global_const_and_loop_declarations

local t = require("support.assertions")

local environment = {}
local declared = assert(load([[
    global answer
    answer = 42
    return answer
]], "declared-global", "t", environment))
t.equal(declared(), 42)
t.equal(environment.answer, 42)

-- 显式 global 声明使同一块中的其他自由名必须声明；语法失败即可证明边界，
-- 不锁定编译器诊断全文。
local invalid, message = load([[
    global allowed
    allowed = 1
    undeclared = 2
]], "global-rules", "t", {})
t.equal(invalid, nil)
t.equal(type(message), "string")

local constant = select(1, load("local x <const> = 1; x = 2", "const", "t"))
t.equal(constant, nil)
local numeric_for = select(1, load("for i = 1, 1 do i = 2 end", "for", "t"))
t.equal(numeric_for, nil)
local generic_for = select(1, load(
    "for key in pairs({value = 1}) do key = 'other' end",
    "generic-for",
    "t"
))
t.equal(generic_for, nil)

t.done()
