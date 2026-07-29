-- Common question: what is imported, cached, and shared between module consumers?
-- Inputs: a Lua module returning a table, two require calls, and export mutation.
-- Observations: module identity, package.loaded caching, shared table fields, and loader data.
-- polyglot-family: modules_packages_and_loading
-- polyglot-concept: modules_imports_linkage_and_live_bindings
-- polyglot-related: languages/lua/tooling_and_runtime/13_modules_and_loading/
-- polyglot-related+: test_099_require_searchers_cache_failures_and_cycles.lua

local t = require("support.assertions")
package.loaded.course_sample = nil

local first, path = require("course_sample")
local second = require("course_sample")
t.same(first, second)
t.equal(type(path), "string")
t.equal(first.answer, 42)

first.mutable = "shared"
t.equal(second.mutable, "shared")
t.same(package.loaded.course_sample, first)

-- require 缓存的是模块返回值；“live”来自共享 table identity，而非特殊 import binding。
t.done()
