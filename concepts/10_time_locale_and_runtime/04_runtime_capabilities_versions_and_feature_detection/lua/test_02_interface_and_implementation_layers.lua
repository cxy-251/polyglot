-- Common question: which observations belong to the language interface versus one implementation?
-- Inputs: Lua/C release strings, numeric configuration, package separators, bytecode, and table capacity hints.
-- Observations: locked public macros, runtime feature APIs, platform configuration, and unstable representations.
-- polyglot-family: time_locale_and_runtime
-- polyglot-concept: runtime_capabilities_versions_and_feature_detection
-- polyglot-related: languages/lua/tooling_and_runtime/16_advanced_c_api_and_compatibility/
-- polyglot-related+: test_128_api_version_and_abi_boundaries.lua

local t = require("support.assertions")
local c_api = require("support.c_api")
local native = require("polyglot_native")

t.equal(_VERSION, "Lua 5.5")
t.equal(native.release, "Lua 5.5.0")
t.matches(c_api.run("version-gc"), "C API case passed: version%-gc")
t.equal(math.type(1), "integer")
t.equal(string.packsize("j"), 8)
t.equal(package.config:sub(1, 1), "/")
t.equal(type(table.create), "function")

local bytecode = string.dump(function() return 42 end)
t.equal(bytecode:sub(1, 4), "\27Lua")

-- ABI、bytecode、对象布局、GC 时机和 table 内存布局不是跨版本语言保证。
t.done()
