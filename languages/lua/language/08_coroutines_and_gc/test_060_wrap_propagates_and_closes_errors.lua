-- polyglot-covers: lua.coroutines.wrap_error_cleanup

local t = require("support.assertions")
local closed = false
local resource = setmetatable({}, {
    __close = function()
        closed = true
    end,
})

local wrapped = coroutine.wrap(function()
    local handle <close> = resource
    t.same(handle, resource)
    coroutine.yield("started")
    error("wrapped failure")
end)

t.equal(wrapped(), "started")
t.raises(wrapped, "wrapped failure")
t.truth(closed)

t.done()
