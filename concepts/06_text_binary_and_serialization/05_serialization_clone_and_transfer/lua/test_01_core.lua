-- Common question: what is copied or preserved by serialization and cloning?
-- Inputs: a nested table, aliases, a deliberate deep clone, and binary scalar encoding.
-- Observations: identity loss, reconstructed sharing policy, immutable bytes, and absent general serializer.
-- polyglot-family: text_binary_and_serialization
-- polyglot-concept: serialization_clone_and_transfer
-- polyglot-related: languages/lua/standard_library/09_strings_patterns_utf8/test_070_binary_pack_and_unpack.lua

local t = require("support.assertions")

local function clone(value, seen)
    if type(value) ~= "table" then return value end
    seen = seen or {}
    if seen[value] then return seen[value] end
    local copy = {}
    seen[value] = copy
    for key, item in pairs(value) do
        copy[clone(key, seen)] = clone(item, seen)
    end
    return copy
end

local shared = {value = 42}
local source = {left = shared, right = shared}
local copied = clone(source)
t.falsey(rawequal(copied, source))
t.falsey(rawequal(copied.left, shared))
t.same(copied.left, copied.right)
t.equal(copied.left.value, 42)

local bytes = string.pack("<i4", 42)
t.equal(string.unpack("<i4", bytes), 42)

-- 标准库没有通用对象序列化器；clone policy、cycles 和 metatable 必须显式决定。
t.done()
