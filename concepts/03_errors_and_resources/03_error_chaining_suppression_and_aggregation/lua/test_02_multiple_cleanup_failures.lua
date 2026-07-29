-- Common question: how are several cleanup failures represented?
-- Inputs: a body failure and two to-be-closed resources that both fail.
-- Observations: reverse cleanup order, current-error handoff, and explicit aggregation.
-- polyglot-family: errors_and_resources
-- polyglot-concept: error_chaining_suppression_and_aggregation
-- polyglot-related: languages/lua/language/07_errors_and_resources/
-- polyglot-related+: test_052_close_order_unwind_and_failure_precedence.lua

local t = require("support.assertions")
local events = {}
local function failing(name)
    return setmetatable({}, {
        __close = function(_, current)
            events[#events + 1] = {name = name, current = current}
            error({kind = "close", name = name, cause = current}, 0)
        end,
    })
end

local ok, final = pcall(function()
    local first <close> = failing("first")
    local second <close> = failing("second")
    t.truth(first and second)
    error({kind = "body"}, 0)
end)
t.falsey(ok)
t.equal(events[1].name, "second")
t.equal(events[1].current.kind, "body")
t.equal(events[2].name, "first")
t.equal(events[2].current.name, "second")
t.equal(final.name, "first")
t.equal(final.cause.name, "second")

t.done()
