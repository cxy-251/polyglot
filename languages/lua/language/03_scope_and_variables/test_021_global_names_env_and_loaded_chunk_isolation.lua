-- polyglot-covers: lua.scope.global_names_and_environments

local t = require("support.assertions")

t.same(_G, _ENV)
local global_environment = _G
local first_environment = {value = 10}
local second_environment = {value = 20}
setmetatable(first_environment, {__index = global_environment})

local source = [[
    value = value + 1
    created = value * 2
    local print_type = type and type(print) or "unavailable"
    return value, created, print_type, _G == _ENV
]]
local first = assert(load(source, "first", "t", first_environment))
local second = assert(load(source, "second", "t", second_environment))

local value, created, print_type, g_is_environment = first()
t.equal(value, 11)
t.equal(created, 22)
t.equal(print_type, "function")
t.falsey(g_is_environment)
t.same(first_environment._G, global_environment)

value, created, print_type, g_is_environment = second()
t.equal(value, 21)
t.equal(created, 42)
t.equal(print_type, "unavailable")
t.falsey(g_is_environment)
t.equal(second_environment.print, nil)
t.equal(rawget(_G, "created"), nil)

t.done()
