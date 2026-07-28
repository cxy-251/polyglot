-- polyglot-covers: lua.c_api.native_userdata_cleanup

local t = require("support.assertions")
local native = require("polyglot_native")
local before = native.finalized_boxes()

do
    local box <close> = native.new_box(40, "owned")
    t.equal(box:get(), 40)
    t.same(box:set(42), box)
    t.equal(box:get(), 42)
    t.equal(box:label(), "owned")
    t.matches(tostring(box), "native_box%(42,open%)")
end

t.equal(native.finalized_boxes(), before + 1)
collectgarbage("collect")
t.equal(native.finalized_boxes(), before + 1)

-- __close 与 __gc 共用幂等 close，防止 double close。
t.done()
