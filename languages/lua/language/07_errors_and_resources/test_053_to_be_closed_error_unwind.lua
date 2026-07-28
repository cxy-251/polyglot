-- polyglot-covers: lua.resources.to_be_closed_error_unwind

local t = require("support.assertions")
local observed
local resource = setmetatable({}, {
    __close = function(_, error_value)
        observed = error_value
    end,
})

local marker = {kind = "body-error"}
local ok, error_value = pcall(function()
    local handle <close> = resource
    t.same(handle, resource)
    error(marker)
end)

t.falsey(ok)
t.same(error_value, marker)
t.same(observed, marker)

t.done()
