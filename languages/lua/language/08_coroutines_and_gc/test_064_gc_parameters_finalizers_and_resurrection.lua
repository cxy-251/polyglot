-- polyglot-covers: lua.gc.parameters_finalizers_and_resurrection

local t = require("support.assertions")
local original_mode = collectgarbage("incremental")
local original_pause = collectgarbage("param", "pause")
t.equal(type(original_pause), "number")
t.equal(collectgarbage("param", "pause", original_pause), original_pause)

local prior = collectgarbage("generational")
t.equal(prior, "incremental")
t.equal(collectgarbage("incremental"), "generational")

local finalized = 0
local resurrected
local weak = setmetatable({}, {__mode = "v"})
do
    local value = setmetatable({answer = 42}, {
        __gc = function(self)
            finalized = finalized + 1
            resurrected = self
        end,
    })
    weak.value = value
end

for _ = 1, 20 do
    collectgarbage("collect")
    if finalized > 0 then
        break
    end
end
t.equal(finalized, 1)
t.equal(resurrected.answer, 42)

resurrected = nil
for _ = 1, 20 do
    collectgarbage("collect")
    if weak.value == nil then
        break
    end
end
t.equal(weak.value, nil)

collectgarbage(original_mode)
t.done()
