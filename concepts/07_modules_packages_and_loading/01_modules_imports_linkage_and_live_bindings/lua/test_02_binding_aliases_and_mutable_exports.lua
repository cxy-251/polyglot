-- Common question: do imported aliases remain live when exports or local bindings change?
-- Inputs: a cached module table, copied scalar field, table alias, and package.loaded replacement.
-- Observations: alias identity, scalar snapshots, field mutation visibility, and future-require behavior.
-- polyglot-family: modules_packages_and_loading
-- polyglot-concept: modules_imports_linkage_and_live_bindings
-- polyglot-related: languages/lua/tooling_and_runtime/13_modules_and_loading/test_099_require_cache_and_lua_modules.lua

local t = require("support.assertions")
package.loaded.course_sample = nil
local exports = require("course_sample")
local alias = exports
local copied_answer = exports.answer

exports.answer = 43
t.equal(alias.answer, 43)
t.equal(copied_answer, 42)

local replacement = {answer = 99}
package.loaded.course_sample = replacement
t.same(require("course_sample"), replacement)
t.same(alias, exports)
t.equal(alias.answer, 43)

t.done()
