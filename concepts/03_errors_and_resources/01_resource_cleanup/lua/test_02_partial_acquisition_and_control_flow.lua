-- Common question: which resources are cleaned when acquisition or control flow stops early?
-- Inputs: two successful acquisitions, one failed acquisition, return, and error.
-- Observations: declaration timing, reverse close order, partial ownership, and nil/false close values.
-- polyglot-family: errors_and_resources
-- polyglot-concept: resource_cleanup
-- polyglot-related: languages/lua/language/07_errors_and_resources/test_052_to_be_closed_normal_exit.lua

local t = require("support.assertions")
local events = {}
local function acquire(name)
    if name == "failed" then
        return nil, "not acquired"
    end
    return setmetatable({name = name}, {
        __close = function(self)
            events[#events + 1] = self.name
        end,
    })
end

local ok = pcall(function()
    local first <close> = assert(acquire("first"))
    local second <close> = assert(acquire("second"))
    local third <close> = assert(acquire("failed"))
    return first, second, third
end)
t.falsey(ok)
t.equal(table.concat(events, ","), "second,first")

do
    local ignored <close> = nil
    t.equal(ignored, nil)
end

t.done()
