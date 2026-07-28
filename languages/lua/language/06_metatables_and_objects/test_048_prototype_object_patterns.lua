-- polyglot-covers: lua.metatables.prototype_object_patterns

local t = require("support.assertions")

local Counter = {}
Counter.__index = Counter

function Counter:new(start)
    return setmetatable({value = start}, self)
end

function Counter:add(amount)
    self.value = self.value + amount
    return self.value
end

local NamedCounter = setmetatable({name = "derived"}, {__index = Counter})
NamedCounter.__index = NamedCounter

local instance = NamedCounter:new(40)
t.equal(instance:add(2), 42)
t.equal(instance.name, "derived")
t.same(getmetatable(instance), NamedCounter)

-- 这是基于 table 和 __index 的惯用模式，不创建名义 class 或 interface。
local looping = {}
setmetatable(looping, {__index = looping})
t.raises(function()
    return looping.missing
end, "__index")

t.done()
