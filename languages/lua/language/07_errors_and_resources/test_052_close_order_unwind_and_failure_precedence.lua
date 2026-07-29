-- polyglot-covers: lua.resources.close_order_unwind_and_failure_precedence

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

do
    local first <close> = resource("normal-first", false)
    local second <close> = resource("normal-second", false)
    t.equal(first.name, "normal-first")
    t.equal(second.name, "normal-second")
end
t.equal(events[1][1], "normal-second")
t.equal(events[2][1], "normal-first")
t.equal(events[1][2], nil)

events = {}
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

-- close 按声明逆序运行；新的 close 错误成为继续传给更早资源的 pending error。
t.done()
