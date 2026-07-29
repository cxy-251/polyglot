-- Common question: how are programmer contracts and operational failures signaled?
-- Inputs: successful/failed assert, explicit error objects, and nil-plus-message results.
-- Observations: returned arguments, raised identity, protected handling, and result protocols.
-- polyglot-family: errors_and_resources
-- polyglot-concept: contracts_assertions_and_failure_signaling
-- polyglot-related: languages/lua/language/07_errors_and_resources/
-- polyglot-related+: test_049_error_values_protected_calls_and_context.lua

local t = require("support.assertions")

local value, extra = assert(42, "kept")
t.equal(value, 42)
t.equal(extra, "kept")

local marker = {kind = "contract"}
local ok, error_value = pcall(assert, false, marker)
t.falsey(ok)
t.same(error_value, marker)

local function lookup(key)
    if key == "answer" then return 42 end
    return nil, "missing key"
end
t.equal(lookup("answer"), 42)
local missing, message = lookup("other")
t.equal(missing, nil)
t.equal(message, "missing key")

t.done()
