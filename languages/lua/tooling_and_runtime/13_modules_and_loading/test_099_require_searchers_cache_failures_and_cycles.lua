-- polyglot-covers: lua.modules.require_searchers_cache_failures_and_cycles

local t = require("support.assertions")
package.loaded.course_sample = nil
local first, loader_data = require("course_sample")
t.same(require("course_sample"), first)
t.equal(first.double(21), 42)
t.equal(first.loaded_as, "course_sample")
t.equal(type(loader_data), "string")

local attempts = 0
package.loaded.polyglot_failure = nil
package.preload.polyglot_failure = function()
    attempts = attempts + 1
    error("fixture failure")
end
t.raises(function() require("polyglot_failure") end, "fixture failure")
t.equal(package.loaded.polyglot_failure, nil)
t.raises(function() require("polyglot_failure") end, "fixture failure")
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

-- require 只缓存成功结果；循环模块必须在递归 require 前显式发布部分 exports。
t.equal(type(package.searchers), "table")
t.truth(#package.searchers >= 4)
t.done()
