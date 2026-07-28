-- polyglot-covers: lua.scope.read_only_declarations_and_loop_variables

local t = require("support.assertions")

local constant_error = select(2, load([[
    local answer <const> = 42
    answer = 43
]], "constant", "t"))
t.matches(constant_error, "const")

local numeric_for_error = select(2, load([[
    for index = 1, 1 do
        index = 2
    end
]], "numeric-for", "t"))
t.matches(numeric_for_error, "const variable")

local generic_for_error = select(2, load([[
    for key in pairs({value = 1}) do
        key = "other"
    end
]], "generic-for", "t"))
t.matches(generic_for_error, "const variable")

t.done()
