-- Common question: when does initialization run, how is it cached, and how are C modules loaded?
-- Inputs: package.preload, package.loaded, repeated require, explicit invalidation, and a C module.
-- Observations: one-time loader execution, cache replacement, dynamic loader path, and registered API.
-- polyglot-family: modules_packages_and_loading
-- polyglot-concept: initialization_caching_cycles_and_dynamic_loading
-- polyglot-related: languages/lua/tooling_and_runtime/13_modules_and_loading/test_103_c_module_loading.lua

local t = require("support.assertions")
local runs = 0
package.preload.polyglot_init = function()
    runs = runs + 1
    return {run = runs}
end
package.loaded.polyglot_init = nil

local first = require("polyglot_init")
local second = require("polyglot_init")
t.same(first, second)
t.equal(runs, 1)

package.loaded.polyglot_init = nil
local third = require("polyglot_init")
t.equal(third.run, 2)
t.falsey(rawequal(third, first))

package.loaded.polyglot_native = nil
local native, path = require("polyglot_native")
t.equal(native.add(20, 22), 42)
t.equal(type(path), "string")

t.done()
