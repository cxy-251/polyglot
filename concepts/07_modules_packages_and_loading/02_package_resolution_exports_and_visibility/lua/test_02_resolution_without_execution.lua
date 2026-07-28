-- Common question: can package resolution be inspected without executing initialization?
-- Inputs: a temporary module file, package.searchpath, package.loaded, and require.
-- Observations: path discovery without execution, first-load side effect, and cache suppression.
-- polyglot-family: modules_packages_and_loading
-- polyglot-concept: package_resolution_exports_and_visibility
-- polyglot-related: languages/lua/tooling_and_runtime/13_modules_and_loading/test_101_searchpath_templates.lua

local t = require("support.assertions")
local root = assert(os.getenv("POLYGLOT_LUA_TEST_TMP"))
local path = root .. "/resolution_probe.lua"
local file = assert(io.open(path, "w"))
assert(file:write([[
_G.polyglot_resolution_runs = (_G.polyglot_resolution_runs or 0) + 1
return {runs = _G.polyglot_resolution_runs}
]]))
assert(file:close())

local module_path = root .. "/?.lua"
local found = assert(package.searchpath("resolution_probe", module_path))
t.equal(found, path)
t.equal(rawget(_G, "polyglot_resolution_runs"), nil)

local original_path = package.path
package.path = module_path
package.loaded.resolution_probe = nil
local value = require("resolution_probe")
package.path = original_path
t.equal(value.runs, 1)
t.equal(polyglot_resolution_runs, 1)
t.same(require("resolution_probe"), value)
t.equal(polyglot_resolution_runs, 1)
t.truth(os.remove(path))

t.done()
