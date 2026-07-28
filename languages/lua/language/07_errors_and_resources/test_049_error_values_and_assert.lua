-- polyglot-covers: lua.errors.error_values_and_assert

local t = require("support.assertions")

local marker = {code = 42}
local ok, value = pcall(function()
    error(marker)
end)
t.falsey(ok)
t.same(value, marker)

local first, second = assert("value", "extra")
t.equal(first, "value")
t.equal(second, "extra")

local assert_ok, assert_error = pcall(assert, false, marker)
t.falsey(assert_ok)
t.same(assert_error, marker)

local nil_error_ok, nil_error = pcall(error, nil)
t.falsey(nil_error_ok)
t.equal(type(nil_error), "string")

t.done()
