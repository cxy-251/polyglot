-- polyglot-covers: lua.metatables.newindex_proxies_and_rawset

local t = require("support.assertions")
local storage = {}
local proxy = setmetatable({}, {
    __index = storage,
    __newindex = function(_, key, value)
        storage[key] = value
    end,
})

proxy.answer = 42
t.equal(storage.answer, 42)
t.equal(proxy.answer, 42)
t.equal(rawget(proxy, "answer"), nil)

rawset(proxy, "answer", 43)
t.equal(proxy.answer, 43)
t.equal(storage.answer, 42)

proxy.answer = 44
t.equal(rawget(proxy, "answer"), 44)
t.equal(storage.answer, 42)

t.done()
