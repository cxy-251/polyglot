-- Common question: when does a lazy producer execute, and can consumers stop early?
-- Inputs: a stateful closure iterator, observable production, and an early break.
-- Observations: demand-driven calls, retained state, no background execution, and unconsumed values.
-- polyglot-family: collections_and_iteration
-- polyglot-concept: generators_laziness_and_early_termination
-- polyglot-related: languages/lua/language/08_coroutines_and_gc/test_059_yield_value_exchange.lua

local t = require("support.assertions")
local produced = 0
local function integers(limit)
    local current = 0
    return function()
        current = current + 1
        if current <= limit then
            produced = produced + 1
            return current
        end
    end
end

local iterator = integers(10)
t.equal(produced, 0)
local observed = {}
for value in iterator do
    observed[#observed + 1] = value
    if value == 3 then break end
end
t.equal(table.concat(observed, ","), "1,2,3")
t.equal(produced, 3)
t.equal(iterator(), 4)
t.equal(produced, 4)

t.done()
