-- polyglot-covers: lua.table_library.compact_array_boundary

local t = require("support.assertions")

local array = table.create(100, 0)
for index = 1, 100 do
    array[index] = index * 2
end
t.equal(#array, 100)
t.equal(array[1], 2)
t.equal(array[100], 200)

array.label = "mixed"
t.equal(array.label, "mixed")
t.equal(rawlen(array), 100)

local map = table.create(0, 20)
map.answer = 42
t.equal(map.answer, 42)

-- table.create 的容量参数是性能提示；array/hash 内部布局和内存占用不是语言保证。
t.done()
