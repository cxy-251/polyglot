-- polyglot-covers: lua.table_library.sequence_mutation_packing_and_capacity

local t = require("support.assertions")
local values = {"a", "c"}

table.insert(values, 2, "b")
t.equal(table.concat(values, ","), "a,b,c")
t.equal(table.remove(values, 2), "b")
t.equal(table.concat(values, "", 1, 2), "ac")

local destination = {}
t.same(table.move(values, 1, 2, 1, destination), destination)
t.equal(table.concat(destination), "ac")

local packed = table.pack("a", nil, "c")
t.equal(packed.n, 3)
t.pack_equal(table.pack(table.unpack(packed, 1, packed.n)), packed)
t.raises(function() table.concat({"a", {}}, ",") end)

local array = table.create(100, 2)
t.equal(next(array), nil)
for index = 1, 100 do
    array[index] = index * 2
end
array.label = "mixed"
t.equal(#array, 100)
t.equal(array.label, "mixed")

-- table.create 的容量仅是性能提示；array/hash 内部布局和内存占用不是公开契约。
t.done()
