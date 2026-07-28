-- Common question: how are causal failures chained or deliberately replaced?
-- Inputs: a lower-level table error, contextual wrapping, and suppression by replacement.
-- Observations: explicit cause fields, arbitrary error values, and absence of native exception chaining.
-- polyglot-family: errors_and_resources
-- polyglot-concept: error_chaining_suppression_and_aggregation
-- polyglot-related: languages/lua/language/07_errors_and_resources/test_056_error_context_without_native_chaining.lua

local t = require("support.assertions")
local function parse()
    error({kind = "parse", input = "bad"}, 0)
end
local function load_value()
    local ok, cause = pcall(parse)
    if not ok then
        error({kind = "load", cause = cause}, 0)
    end
end

local ok, chained = pcall(load_value)
t.falsey(ok)
t.equal(chained.kind, "load")
t.equal(chained.cause.kind, "parse")

local suppressed_ok, replacement = pcall(function()
    local inner_ok = pcall(parse)
    if not inner_ok then error("public failure", 0) end
end)
t.falsey(suppressed_ok)
t.equal(replacement, "public failure")

t.done()
