-- polyglot-covers: lua.gc.modes_weak_tables_finalization_and_resurrection

local t = require("support.assertions")
local original_mode = collectgarbage("incremental")
local original_pause = collectgarbage("param", "pause")

t.with_cleanup(function()
    t.truth(original_mode == "incremental" or original_mode == "generational")
    t.truth(collectgarbage("isrunning"))
    t.equal(type(collectgarbage("count")), "number")
    t.equal(type(collectgarbage("step", 0)), "boolean")

    local weak_values = setmetatable({}, {__mode = "v"})
    do
        weak_values.item = {}
    end
    collectgarbage("collect")
    t.equal(weak_values.item, nil)

    -- weak-key table 是 ephemeron：仅从 value 反向引用 key 不会让这对对象存活。
    local ephemeron = setmetatable({}, {__mode = "k"})
    do
        local key = {}
        ephemeron[key] = {back_reference = key}
    end
    collectgarbage("collect")
    t.equal(next(ephemeron), nil)

    local finalized = 0
    local resurrected
    do
        local value = setmetatable({answer = 42}, {
            __gc = function(self)
                finalized = finalized + 1
                resurrected = self
            end,
        })
        t.equal(value.answer, 42)
    end
    collectgarbage("collect")
    t.equal(finalized, 1)
    t.equal(resurrected.answer, 42)

    -- resurrection 使对象本轮重新可达；释放最后引用后，后续完整周期才回收它。
    local weak = setmetatable({value = resurrected}, {__mode = "v"})
    resurrected = nil
    collectgarbage("collect")
    collectgarbage("collect")
    t.equal(weak.value, nil)

    -- 参数是调优接口而非性能保证；课程只验证读写契约并恢复原值。
    t.equal(collectgarbage("param", "pause", original_pause), original_pause)
end, function()
    collectgarbage("param", "pause", original_pause)
    collectgarbage(original_mode)
end)

t.done()
