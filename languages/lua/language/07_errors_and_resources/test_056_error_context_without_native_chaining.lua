-- polyglot-covers: lua.errors.explicit_error_context

local t = require("support.assertions")

local function inner()
    error({kind = "parse", input = "bad"})
end

local function outer()
    local ok, cause = pcall(inner)
    if not ok then
        error({kind = "load", cause = cause}, 0)
    end
end

local ok, error_value = pcall(outer)
t.falsey(ok)
t.equal(error_value.kind, "load")
t.equal(error_value.cause.kind, "parse")
t.equal(error_value.cause.input, "bad")

-- Lua 错误对象可以是任意值；错误链需要应用显式建模，不存在内建 exception class。
t.equal(getmetatable(error_value), nil)

t.done()
