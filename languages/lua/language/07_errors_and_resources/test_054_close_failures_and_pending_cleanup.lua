-- polyglot-covers: lua.resources.close_failures_and_pending_cleanup

local t = require("support.assertions")
local events = {}

local function resource(name, fails)
    return setmetatable({name = name}, {
        __close = function(self, prior_error)
            events[#events + 1] = {self.name, prior_error}
            if fails then
                error("close failed: " .. self.name)
            end
        end,
    })
end

local ok, final_error = pcall(function()
    local first <close> = resource("first", false)
    local second <close> = resource("second", true)
    t.equal(first.name, "first")
    t.equal(second.name, "second")
    error("body failed")
end)

t.falsey(ok)
t.matches(final_error, "close failed: second")
t.equal(events[1][1], "second")
t.matches(events[1][2], "body failed")
t.equal(events[2][1], "first")
t.matches(events[2][2], "close failed: second")

t.done()
