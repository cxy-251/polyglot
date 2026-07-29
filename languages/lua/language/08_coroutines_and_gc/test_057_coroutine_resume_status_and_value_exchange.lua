-- polyglot-covers: lua.coroutines.resume_status_and_value_exchange

local t = require("support.assertions")
local worker
worker = coroutine.create(function(first, second)
    local running, is_main = coroutine.running()
    t.same(running, worker)
    t.falsey(is_main)
    local left, right = coroutine.yield(first + second, first * second)
    return left + right, "done"
end)

t.equal(coroutine.status(worker), "suspended")
local ok, sum, product = coroutine.resume(worker, 6, 7)
t.truth(ok)
t.equal(sum, 13)
t.equal(product, 42)
t.equal(coroutine.status(worker), "suspended")

local completed, resumed, marker = coroutine.resume(worker, 20, 22)
t.truth(completed)
t.equal(resumed, 42)
t.equal(marker, "done")
t.equal(coroutine.status(worker), "dead")

local failed, message = coroutine.resume(worker)
t.falsey(failed)
t.equal(type(message), "string")

-- coroutine 是协作式控制流，不是 OS thread；resume 参数成为入口或 yield 的返回值。
t.done()
