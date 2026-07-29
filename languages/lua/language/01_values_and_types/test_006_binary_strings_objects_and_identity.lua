-- polyglot-covers: lua.values.binary_strings_objects_and_identity

local t = require("support.assertions")

-- string 是不可变字节序列；内容相等是值语义，驻留地址不是公开契约。
local binary = "A\0B\255"
t.equal(#binary, 4)
t.equal(binary, string.char(65, 0, 66, 255))
t.truth(rawequal("poly" .. "glot", "polyglot"))

-- table、function、thread 与 full userdata 是对象；赋值和传参复制引用。
local table_value = {}
local alias = table_value
t.same(alias, table_value)
t.falsey(rawequal(table_value, {}))

local function callable()
    return 42
end
t.same(callable, callable)
t.falsey(rawequal(callable, function() return 42 end))

local thread = coroutine.create(function() return "done" end)
t.equal(type(thread), "thread")
t.same(thread, thread)

local file = assert(io.tmpfile())
t.equal(type(file), "userdata")
t.equal(io.type(file), "file")
t.truth(file:close())
t.equal(io.type(file), "closed file")

t.done()
