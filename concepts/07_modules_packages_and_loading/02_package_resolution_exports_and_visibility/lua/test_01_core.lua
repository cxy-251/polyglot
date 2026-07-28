-- Common question: how are modules resolved and which names become visible?
-- Inputs: package.path templates, returned exports, module-local variables, and _G.
-- Observations: searchpath substitution, explicit exports, lexical privacy, and no package manager.
-- polyglot-family: modules_packages_and_loading
-- polyglot-concept: package_resolution_exports_and_visibility
-- polyglot-related: languages/lua/tooling_and_runtime/13_modules_and_loading/test_101_searchpath_templates.lua

local t = require("support.assertions")
local resolved = assert(package.searchpath("course_sample", package.path))
t.matches(resolved, "course_sample%.lua")

package.loaded.course_sample = nil
local exports = require("course_sample")
t.equal(exports.answer, 42)
t.equal(exports.double(21), 42)
t.equal(rawget(_G, "module"), nil)
t.equal(rawget(_G, "answer"), nil)

local missing, message = package.searchpath("not.present", package.path)
t.equal(missing, nil)
t.matches(message, "not/present%.lua")

-- Lua 发行版没有 package manager；解析仅由 loader、searcher 和路径模板构成。
t.done()
