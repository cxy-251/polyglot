-- polyglot-covers: lua.coroutines.explicit_close

local t = require("support.assertions")
local events = {}
local resource = setmetatable({}, {
    __close = function(_, error_value)
        events[#events + 1] = {error_value}
    end,
})

local worker = coroutine.create(function()
    local handle <close> = resource
    t.same(handle, resource)
    coroutine.yield("suspended")
end)

local ok, marker = coroutine.resume(worker)
t.truth(ok)
t.equal(marker, "suspended")
t.equal(#events, 0)

local closed, error_value = coroutine.close(worker)
t.truth(closed)
t.equal(error_value, nil)
t.equal(#events, 1)
t.equal(events[1][1], nil)
t.equal(coroutine.status(worker), "dead")

t.done()
