-- polyglot-covers: lua.coroutines.yield_value_exchange

local t = require("support.assertions")
local worker = coroutine.create(function(initial)
    local left, right = coroutine.yield("ready", initial)
    local final = coroutine.yield(left + right)
    return final
end)

local ok, marker, initial = coroutine.resume(worker, 10)
t.truth(ok)
t.equal(marker, "ready")
t.equal(initial, 10)

local yielded
ok, yielded = coroutine.resume(worker, 20, 22)
t.truth(ok)
t.equal(yielded, 42)

local final
ok, final = coroutine.resume(worker, "complete")
t.truth(ok)
t.equal(final, "complete")

t.done()
