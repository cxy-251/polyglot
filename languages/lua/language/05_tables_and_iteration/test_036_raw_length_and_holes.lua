-- polyglot-covers: lua.tables.raw_length_and_holes

local t = require("support.assertions")

local value = setmetatable({10, 20, 30}, {
    __len = function()
        return 99
    end,
})

t.equal(#value, 99)
t.equal(rawlen(value), 3)

value[2] = nil
t.equal(value[1], 10)
t.equal(value[2], nil)
t.equal(value[3], 30)

local border = rawlen(value)
t.truth((border == 0 or value[border] ~= nil) and value[border + 1] == nil)
t.equal(rawlen("a\0b"), 3)

t.done()
