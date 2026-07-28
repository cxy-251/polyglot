-- polyglot-covers: lua.values.userdata_and_threads

local t = require("support.assertions")

local file = assert(io.tmpfile())
t.equal(type(file), "userdata")
t.truth(io.type(file) == "file")
t.equal(file:write("lua"), file)
t.equal(file:seek("set", 0), 0)
t.equal(file:read("a"), "lua")
t.truth(file:close())
t.equal(io.type(file), "closed file")

local thread = coroutine.create(function()
    return "done"
end)
t.equal(type(thread), "thread")
t.equal(coroutine.status(thread), "suspended")
local ok, value = coroutine.resume(thread)
t.truth(ok)
t.equal(value, "done")
t.equal(coroutine.status(thread), "dead")

t.done()
