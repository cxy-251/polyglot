-- polyglot-covers: lua.scope.load_environment_isolation

local t = require("support.assertions")

local first_environment = {value = 10}
local second_environment = {value = 20}
local source = "value = value + 1; created = value * 2; return value, created"

local first = assert(load(source, "first", "t", first_environment))
local second = assert(load(source, "second", "t", second_environment))

local first_value, first_created = first()
local second_value, second_created = second()
t.equal(first_value, 11)
t.equal(first_created, 22)
t.equal(second_value, 21)
t.equal(second_created, 42)
t.equal(first_environment.value, 11)
t.equal(second_environment.value, 21)
t.equal(rawget(_G, "created"), nil)

t.done()
