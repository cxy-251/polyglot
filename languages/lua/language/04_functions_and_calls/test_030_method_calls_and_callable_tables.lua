-- polyglot-covers: lua.functions.method_calls_and_callable_tables

local t = require("support.assertions")

local receiver = {value = 40}

function receiver:add(amount)
    return self.value + amount
end

t.equal(receiver:add(2), 42)
t.equal(receiver.add(receiver, 2), 42)

local callable = setmetatable({base = 40}, {
    __call = function(self, amount)
        return self.base + amount
    end,
})

t.equal(callable(2), 42)
t.equal(type(callable), "table")

t.done()
