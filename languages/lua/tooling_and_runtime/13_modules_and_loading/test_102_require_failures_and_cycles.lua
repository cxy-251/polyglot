-- polyglot-covers: lua.modules.require_failures_and_cycles

local t = require("support.assertions")
local attempts = 0
package.loaded.polyglot_failure = nil
package.preload.polyglot_failure = function()
    attempts = attempts + 1
    error("fixture failure")
end

t.raises(function()
    require("polyglot_failure")
end, "fixture failure")
t.equal(package.loaded.polyglot_failure, nil)
t.raises(function()
    require("polyglot_failure")
end, "fixture failure")
t.equal(attempts, 2)

package.loaded.polyglot_cycle_a = nil
package.loaded.polyglot_cycle_b = nil
package.preload.polyglot_cycle_a = function()
    local exports = {name = "a"}
    package.loaded.polyglot_cycle_a = exports
    exports.other = require("polyglot_cycle_b")
    return exports
end
package.preload.polyglot_cycle_b = function()
    return {name = "b", other = require("polyglot_cycle_a")}
end

local cycle = require("polyglot_cycle_a")
t.equal(cycle.other.name, "b")
t.same(cycle.other.other, cycle)

t.done()
