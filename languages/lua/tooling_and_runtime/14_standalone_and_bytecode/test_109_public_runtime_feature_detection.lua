-- polyglot-covers: lua.runtime.public_feature_detection

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

local separator = package.config:sub(1, 1)
t.equal(type(separator), "string")
t.equal(#separator, 1)

-- _VERSION 只给语言系列；精确 patch release、可执行路径、数值宽度和 ABI 配对属于 harness。
t.done()
