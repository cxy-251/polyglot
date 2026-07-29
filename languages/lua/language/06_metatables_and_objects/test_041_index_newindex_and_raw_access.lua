-- polyglot-covers: lua.metatables.index_newindex_and_raw_access

local t = require("support.assertions")

local prototype = {kind = "prototype", answer = 42}
local object = setmetatable({own = "field"}, {__index = prototype})
t.equal(object.own, "field")
t.equal(object.kind, "prototype")
t.equal(rawget(object, "kind"), nil)

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

-- rawset 创建真实字段后，同一键不再触发 __newindex；普通字段始终优先于 fallback。
rawset(proxy, "answer", 43)
proxy.answer = 44
t.equal(rawget(proxy, "answer"), 44)
t.equal(storage.answer, 42)

local recursive = {}
setmetatable(recursive, {__index = recursive})
t.raises(function() return recursive.missing end)

t.done()
