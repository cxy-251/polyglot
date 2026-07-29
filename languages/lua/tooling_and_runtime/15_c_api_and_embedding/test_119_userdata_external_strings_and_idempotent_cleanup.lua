-- polyglot-covers: lua.c_api.userdata_external_strings_and_cleanup

local t = require("support.assertions")
local c_api = require("support.c_api")
local native = require("polyglot_native")

t.matches(c_api.run("userdata"), "C API case passed: userdata")
t.matches(c_api.run("external-string"), "C API case passed: external%-string")

local before = native.finalized_boxes()
do
    local box <close> = native.new_box(40, "owned")
    t.equal(box:get(), 40)
    t.same(box:set(42), box)
    t.equal(box:label(), "owned")
    t.matches(tostring(box), "native_box%(42,open%)")
end
t.equal(native.finalized_boxes(), before + 1)
collectgarbage("collect")
t.equal(native.finalized_boxes(), before + 1)

-- full userdata 由 Lua 管理对象生命周期，user values 维持 Lua 引用；__close 与 __gc
-- 必须共享幂等释放。external string 的外部 buffer 直到 allocator callback 才能释放。
t.done()
