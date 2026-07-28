-- polyglot-covers: lua.modules.require_cache

local t = require("support.assertions")
package.loaded.course_sample = nil

local first, loader_data = require("course_sample")
local second = require("course_sample")

t.same(first, second)
t.equal(first.answer, 42)
t.equal(first.double(21), 42)
t.equal(first.loaded_as, "course_sample")
t.equal(type(loader_data), "string")
t.matches(loader_data, "course_sample%.lua")
t.same(package.loaded.course_sample, first)

package.loaded.course_sample = nil
local reloaded = require("course_sample")
t.falsey(rawequal(reloaded, first))
t.equal(reloaded.answer, 42)

t.done()
