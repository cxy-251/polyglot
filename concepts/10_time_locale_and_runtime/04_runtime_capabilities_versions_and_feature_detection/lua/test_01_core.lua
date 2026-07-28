-- Common question: how can code detect runtime version and optional capabilities?
-- Inputs: _VERSION, standard-library fields, Lua 5.5 additions, and absent APIs.
-- Observations: language-series string, callable checks, feature detection, and release-level limit.
-- polyglot-family: time_locale_and_runtime
-- polyglot-concept: runtime_capabilities_versions_and_feature_detection
-- polyglot-related: languages/lua/tooling_and_runtime/14_standalone_and_bytecode/
-- polyglot-related+: test_109_runtime_version_and_configuration.lua

local t = require("support.assertions")

t.equal(_VERSION, "Lua 5.5")
t.equal(type(table.create), "function")
t.equal(type(coroutine.close), "function")
t.equal(type(collectgarbage), "function")
t.equal(rawget(coroutine, "timeout"), nil)
t.equal(rawget(_G, "async"), nil)

local named_vararg = load("return function(... args) return args.n end", "feature", "t")
t.equal(type(named_vararg), "function")
t.equal(named_vararg()("a", "b"), 2)

-- _VERSION 只给 major.minor；精确 5.5.0 由 lua -v、luac -v 与 C header/library 共同检查。
t.done()
