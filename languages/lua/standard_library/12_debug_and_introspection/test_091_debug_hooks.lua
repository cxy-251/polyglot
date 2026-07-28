-- polyglot-covers: lua.debug.hooks

local t = require("support.assertions")
local prior_hook, prior_mask, prior_count = debug.gethook()
local calls = 0

debug.sethook(function(event)
    if event == "count" then
        calls = calls + 1
    end
end, "", 10)

local total = 0
for index = 1, 100 do
    total = total + index
end
debug.sethook(prior_hook, prior_mask, prior_count)

t.equal(total, 5050)
t.truth(calls > 0)
local restored_hook, restored_mask, restored_count = debug.gethook()
t.same(restored_hook, prior_hook)
t.equal(restored_mask, prior_mask)
t.equal(restored_count, prior_count)

t.done()
