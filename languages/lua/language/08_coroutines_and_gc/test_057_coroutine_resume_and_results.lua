-- polyglot-covers: lua.coroutines.resume_and_results

local t = require("support.assertions")
local worker = coroutine.create(function(first, second)
    local resumed = coroutine.yield(first + second, first * second)
    return resumed, "done"
end)

t.equal(coroutine.status(worker), "suspended")
local ok, sum, product = coroutine.resume(worker, 6, 7)
t.truth(ok)
t.equal(sum, 13)
t.equal(product, 42)
t.equal(coroutine.status(worker), "suspended")

local completed, resumed, marker = coroutine.resume(worker, "continue")
t.truth(completed)
t.equal(resumed, "continue")
t.equal(marker, "done")
t.equal(coroutine.status(worker), "dead")

t.done()
