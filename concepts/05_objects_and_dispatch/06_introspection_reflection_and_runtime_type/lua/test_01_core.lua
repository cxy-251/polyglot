-- Common question: what runtime type and reflective information can code inspect?
-- Inputs: primitive values, metatable names, functions, locals, upvalues, and registry access.
-- Observations: type granularity, protocol identity, debug metadata, and privilege boundary.
-- polyglot-family: objects_and_dispatch
-- polyglot-concept: introspection_reflection_and_runtime_type
-- polyglot-related: languages/lua/standard_library/12_debug_and_introspection/test_089_function_information.lua

local t = require("support.assertions")

t.equal(type(42), "number")
t.equal(math.type(42), "integer")
t.equal(math.type(42.0), "float")

local value = setmetatable({}, {__name = "NamedValue"})
t.equal(type(value), "table")
t.equal(getmetatable(value).__name, "NamedValue")

local captured = 42
local function function_value() return captured end
local info = debug.getinfo(function_value, "Su")
t.equal(info.what, "Lua")
t.equal(info.nups, 1)
local name, upvalue = debug.getupvalue(function_value, 1)
t.equal(name, "captured")
t.equal(upvalue, 42)
t.equal(type(debug.getregistry()), "table")

t.done()
