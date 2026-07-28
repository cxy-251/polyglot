-- Common question: how do inherited lookup, override dispatch, and super calls work?
-- Inputs: chained __index tables, an override, an explicit base call, and missing members.
-- Observations: prototype lookup, receiver preservation, manual super, and absence of nominal inheritance.
-- polyglot-family: objects_and_dispatch
-- polyglot-concept: inheritance_dynamic_dispatch_and_super
-- polyglot-related: languages/lua/language/06_metatables_and_objects/test_048_prototype_object_patterns.lua

local t = require("support.assertions")
local Base = {}
Base.__index = Base
function Base:greet()
    return "base:" .. self.name
end

local Derived = setmetatable({}, {__index = Base})
Derived.__index = Derived
function Derived:greet()
    return Base.greet(self) .. ":derived"
end

local object = setmetatable({name = "lua"}, Derived)
t.equal(object:greet(), "base:lua:derived")
t.same(getmetatable(object), Derived)
t.same(getmetatable(Derived).__index, Base)
t.equal(object.missing, nil)

-- 这里是 table fallback 链；Lua 本身没有 class、interface、MRO 或内建 super。
t.done()
