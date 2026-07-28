-- Common question: which invalid states fail during loading versus execution?
-- Inputs: malformed syntax, undeclared 5.5 globals, type errors, and missing modules.
-- Observations: load-time diagnostics, runtime pcall results, and require search reports.
-- polyglot-family: errors_and_resources
-- polyglot-concept: contracts_assertions_and_failure_signaling
-- polyglot-related: languages/lua/tooling_and_runtime/14_standalone_and_bytecode/test_112_lua_54_to_55_changes.lua

local t = require("support.assertions")

local syntax, syntax_error = load("local =", "syntax", "t")
t.equal(syntax, nil)
t.matches(syntax_error, "<name> expected")

local undeclared, declaration_error = load(
    "global allowed; return missing",
    "global-contract",
    "t",
    {}
)
t.equal(undeclared, nil)
t.matches(declaration_error, "missing")

t.raises(function() return 1 + {} end, "arithmetic")
t.raises(function() require("polyglot_module_that_does_not_exist") end, "not found")

t.done()
