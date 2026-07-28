-- Common question: what happens when cleanup and the body both fail?
-- Inputs: a body error, __close inspection, a closing error, and explicit rethrow.
-- Observations: current error passed to cleanup, replacement precedence, and original identity.
-- polyglot-family: errors_and_resources
-- polyglot-concept: exception_propagation_and_matching
-- polyglot-related: languages/lua/language/07_errors_and_resources/test_054_close_failures_and_pending_cleanup.lua

local t = require("support.assertions")
local original = {kind = "body"}
local seen
local resource = setmetatable({}, {
    __close = function(_, current)
        seen = current
        error({kind = "close", cause = current}, 0)
    end,
})

local ok, final = pcall(function()
    local handle <close> = resource
    t.same(handle, resource)
    error(original)
end)
t.falsey(ok)
t.same(seen, original)
t.equal(final.kind, "close")
t.same(final.cause, original)

local rethrow_ok, rethrown = pcall(function()
    local inner_ok, inner_error = pcall(function() error(original) end)
    if not inner_ok then error(inner_error) end
end)
t.falsey(rethrow_ok)
t.same(rethrown, original)

t.done()
