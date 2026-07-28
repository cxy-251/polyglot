-- polyglot-covers: lua.coroutines.yieldability_boundaries

local t = require("support.assertions")
local main_thread, is_main = coroutine.running()
t.truth(is_main)
t.falsey(coroutine.isyieldable(main_thread))

local worker = coroutine.create(function()
    t.truth(coroutine.isyieldable())
    table.sort({2, 1}, function(left, right)
        coroutine.yield("inside comparator")
        return left < right
    end)
end)

local ok, error_value = coroutine.resume(worker)
t.falsey(ok)
t.matches(error_value, "yield")
t.equal(coroutine.status(worker), "dead")

t.done()
