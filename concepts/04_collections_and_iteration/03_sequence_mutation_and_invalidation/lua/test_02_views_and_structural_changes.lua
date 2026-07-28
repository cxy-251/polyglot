-- Common question: do subcollections alias storage, and what invalidates a view?
-- Inputs: table aliases, table.move copies, nested references, and source mutation.
-- Observations: alias visibility, independent top-level structure, shallow-copy sharing, and no native views.
-- polyglot-family: collections_and_iteration
-- polyglot-concept: sequence_mutation_and_invalidation
-- polyglot-related: languages/lua/language/01_values_and_types/test_007_reference_identity.lua

local t = require("support.assertions")
local source = {{value = 1}, {value = 2}, {value = 3}}
local alias = source
local copied = {}
table.move(source, 1, 2, 1, copied)

alias[1] = {value = 10}
t.equal(source[1].value, 10)
t.equal(copied[1].value, 1)

copied[2].value = 20
t.equal(source[2].value, 20)

table.remove(source, 1)
t.equal(#source, 2)
t.equal(#copied, 2)
t.falsey(rawequal(source, copied))

-- Lua table 没有内建 slice view；复制的是引用值，嵌套对象仍可共享。
t.done()
