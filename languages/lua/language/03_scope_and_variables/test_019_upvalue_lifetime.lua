-- polyglot-covers: lua.scope.upvalue_lifetime

local t = require("support.assertions")

local function counter(start)
    local current = start
    return function(step)
        current = current + (step or 1)
        return current
    end
end

local next_value = counter(10)
t.equal(next_value(), 11)
t.equal(next_value(4), 15)

collectgarbage("collect")
t.equal(next_value(), 16)

local separate = counter(10)
t.equal(separate(), 11)
t.equal(next_value(), 17)

t.done()
