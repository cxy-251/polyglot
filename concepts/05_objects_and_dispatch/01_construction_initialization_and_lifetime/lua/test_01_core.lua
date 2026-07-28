-- Common question: how are objects initialized, owned, finalized, and explicitly closed?
-- Inputs: factory-created tables, metatables, __close, __gc, and aliases.
-- Observations: explicit initialization, reference identity, deterministic close, and eventual finalization.
-- polyglot-family: objects_and_dispatch
-- polyglot-concept: construction_initialization_and_lifetime
-- polyglot-related: languages/lua/language/06_metatables_and_objects/test_048_prototype_object_patterns.lua

local t = require("support.assertions")
local closed = 0
local prototype = {}
prototype.__index = prototype
prototype.__close = function(self)
    if not self.closed then
        self.closed = true
        closed = closed + 1
    end
end

function prototype:new(value)
    return setmetatable({value = value, closed = false}, self)
end

do
    local object <close> = prototype:new(42)
    local alias = object
    t.same(alias, object)
    t.equal(object.value, 42)
end
t.equal(closed, 1)

-- Lua 没有构造器或析构器语言类别；factory、metatable 和关闭协议是分离机制。
t.done()
