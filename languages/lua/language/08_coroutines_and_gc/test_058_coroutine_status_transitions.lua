-- polyglot-covers: lua.coroutines.status_transitions

local t = require("support.assertions")
local outer
local inner
inner = coroutine.create(function()
    t.equal(coroutine.status(outer), "normal")
    local running, is_main = coroutine.running()
    t.same(running, inner)
    t.falsey(is_main)
    return "inner-result"
end)

outer = coroutine.create(function()
    t.equal(coroutine.status(inner), "suspended")
    local ok, result = coroutine.resume(inner)
    t.truth(ok)
    t.equal(result, "inner-result")
    t.equal(coroutine.status(inner), "dead")
    return "outer-result"
end)

local ok, result = coroutine.resume(outer)
t.truth(ok)
t.equal(result, "outer-result")
t.equal(coroutine.status(outer), "dead")

t.done()
