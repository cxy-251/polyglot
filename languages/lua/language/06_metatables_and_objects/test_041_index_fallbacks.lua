-- polyglot-covers: lua.metatables.index_fallbacks

local t = require("support.assertions")

local prototype = {kind = "prototype", answer = 42}
local object = setmetatable({own = "field"}, {__index = prototype})
t.equal(object.own, "field")
t.equal(object.kind, "prototype")
t.equal(rawget(object, "kind"), nil)

local requested = {}
local dynamic
dynamic = setmetatable({}, {
    __index = function(self, key)
        t.same(self, dynamic)
        requested[#requested + 1] = key
        return "<" .. key .. ">"
    end,
})
t.equal(dynamic.missing, "<missing>")
t.equal(requested[1], "missing")

t.done()
