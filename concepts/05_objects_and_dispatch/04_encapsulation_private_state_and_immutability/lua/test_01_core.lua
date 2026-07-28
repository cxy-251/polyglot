-- Common question: how are private state and immutability expressed?
-- Inputs: closure-held state, read-only proxy writes, raw access, and const bindings.
-- Observations: lexical privacy, proxy enforcement, debug privilege, and shallow const semantics.
-- polyglot-family: objects_and_dispatch
-- polyglot-concept: encapsulation_private_state_and_immutability
-- polyglot-related: languages/lua/standard_library/12_debug_and_introspection/
-- polyglot-related+: test_096_debug_library_privilege_boundary.lua

local t = require("support.assertions")

local function counter(initial)
    local value = initial
    return {
        get = function() return value end,
        add = function(amount) value = value + amount end,
    }
end
local object = counter(40)
object.add(2)
t.equal(object.get(), 42)
t.equal(rawget(object, "value"), nil)

local backing = {answer = 42}
local readonly = setmetatable({}, {
    __index = backing,
    __newindex = function() error("read only") end,
})
t.equal(readonly.answer, 42)
t.raises(function() readonly.answer = 43 end, "read only")

local mutable <const> = {value = 1}
mutable.value = 2
t.equal(mutable.value, 2)

t.done()
