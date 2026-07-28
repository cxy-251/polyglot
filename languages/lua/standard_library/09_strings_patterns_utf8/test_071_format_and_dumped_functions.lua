-- polyglot-covers: lua.strings.format_and_dump

local t = require("support.assertions")

t.equal(string.format("%04d", 42), "0042")
local quoted = string.format("%q", "a\nb")
t.equal(assert(load("return " .. quoted, "quoted", "t"))(), "a\nb")
t.equal(string.format("%.2f", 1.25), "1.25")
t.equal(string.format("%x", 255), "ff")

local function add(left, right)
    return left + right
end
local bytecode = string.dump(add, true)
t.equal(type(bytecode), "string")
t.truth(#bytecode > 0)

local loaded = assert(load(bytecode, "dumped", "b"))
t.equal(loaded(20, 22), 42)
t.equal(select(1, load(bytecode, "text-only", "t")), nil)

-- 预编译 chunk 只适合同版本兼容构建，不是安全或跨版本的发布格式。
t.done()
