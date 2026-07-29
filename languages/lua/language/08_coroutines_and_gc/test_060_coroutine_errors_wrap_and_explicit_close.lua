-- polyglot-covers: lua.coroutines.errors_wrap_and_explicit_close

local t = require("support.assertions")
local events = {}
local resource = setmetatable({}, {
    __close = function(_, error_value)
        events[#events + 1] = error_value or false
    end,
})

local worker = coroutine.create(function()
    local handle <close> = resource
    t.same(handle, resource)
    coroutine.yield("suspended")
end)
t.pack_equal(table.pack(coroutine.resume(worker)), {n = 2, true, "suspended"})
t.equal(#events, 0)
local closed, close_error = coroutine.close(worker)
t.truth(closed)
t.equal(close_error, nil)
t.equal(events[1], false)
t.equal(coroutine.status(worker), "dead")

events = {}
local wrapped = coroutine.wrap(function()
    local handle <close> = resource
    t.same(handle, resource)
    coroutine.yield("started")
    error("wrapped failure")
end)
t.equal(wrapped(), "started")
t.raises(wrapped, "wrapped failure")
t.truth(events[1] ~= nil)

-- resume 把失败作为 false/error 返回；wrap 则重新抛出，并在 5.5 中关闭失败 coroutine。
t.done()
