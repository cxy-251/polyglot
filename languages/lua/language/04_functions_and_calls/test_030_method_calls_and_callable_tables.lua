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

local captured = table.pack(receiver:add(2))
t.equal(captured.n, 1)
t.equal(captured[1], 42)

t.done()
