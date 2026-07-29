-- Common question: what cache state remains after failed or cyclic initialization?
-- Inputs: a failing preload loader, retry, and two explicitly cycle-safe modules.
-- Observations: failure is not cached, retries rerun, manual early cache entry, and shared cycle identity.
-- polyglot-family: modules_packages_and_loading
-- polyglot-concept: initialization_caching_cycles_and_dynamic_loading
-- polyglot-related: languages/lua/tooling_and_runtime/13_modules_and_loading/
-- polyglot-related+: test_099_require_searchers_cache_failures_and_cycles.lua

local t = require("support.assertions")
local attempts = 0
package.preload.failed_module = function()
    attempts = attempts + 1
    error("load failed")
end
package.loaded.failed_module = nil

t.raises(function() require("failed_module") end, "load failed")
t.equal(package.loaded.failed_module, nil)
t.raises(function() require("failed_module") end, "load failed")
t.equal(attempts, 2)

package.preload.cycle_a = function()
    local exports = {name = "a"}
    package.loaded.cycle_a = exports
    exports.other = require("cycle_b")
    return exports
end
package.preload.cycle_b = function()
    return {name = "b", other = require("cycle_a")}
end
local cycle = require("cycle_a")
t.equal(cycle.other.name, "b")
t.same(cycle.other.other, cycle)

t.done()
