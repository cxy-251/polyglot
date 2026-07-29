-- Common question: which invalid states fail during loading versus execution?
-- Inputs: malformed syntax, undeclared 5.5 globals, type errors, and missing modules.
-- Observations: load-time diagnostics, runtime pcall results, and require search reports.
-- polyglot-family: errors_and_resources
-- polyglot-concept: contracts_assertions_and_failure_signaling
-- polyglot-related: languages/lua/language/03_scope_and_variables/
-- polyglot-related+: test_023_global_const_and_loop_declarations.lua

local t = require("support.assertions")

local syntax, syntax_error = load("local =", "syntax", "t")
t.equal(syntax, nil)
t.equal(type(syntax_error), "string")

local undeclared, declaration_error = load(
    "global allowed; return missing",
    "global-contract",
    "t",
    {}
)
t.equal(undeclared, nil)
t.equal(type(declaration_error), "string")

t.raises(function() return 1 + {} end)
t.raises(function() require("polyglot_module_that_does_not_exist") end)

t.done()
