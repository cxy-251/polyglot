-- polyglot-covers: lua.debug.hooks_tracebacks_and_restoration

local t = require("support.assertions")
local prior_hook, prior_mask, prior_count = debug.gethook()
local calls = 0

t.with_cleanup(function()
    debug.sethook(function(event)
        if event == "count" then calls = calls + 1 end
    end, "", 10)
    local total = 0
    for index = 1, 100 do total = total + index end
    t.equal(total, 5050)
    t.truth(calls > 0)

    local traceback = debug.traceback("marker", 1)
    t.matches(traceback, "marker")
    t.matches(traceback, "stack traceback")
end, function()
    debug.sethook(prior_hook, prior_mask, prior_count)
end)

local restored_hook, restored_mask, restored_count = debug.gethook()
t.same(restored_hook, prior_hook)
t.equal(restored_mask, prior_mask)
t.equal(restored_count, prior_count)

t.done()
