-- polyglot-covers: lua.gc.modes_steps_and_weak_references

local t = require("support.assertions")
local previous_mode = collectgarbage("incremental")
t.truth(previous_mode == "incremental" or previous_mode == "generational")
t.truth(collectgarbage("isrunning"))
t.equal(type(collectgarbage("count")), "number")
t.equal(type(collectgarbage("step", 0)), "boolean")

local weak = setmetatable({}, {__mode = "v"})
do
    weak.value = {}
end
for _ = 1, 20 do
    collectgarbage("collect")
    if weak.value == nil then
        break
    end
end
t.equal(weak.value, nil)

collectgarbage(previous_mode)
t.done()
