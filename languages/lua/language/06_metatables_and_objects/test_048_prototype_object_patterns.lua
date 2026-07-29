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
-- `new`、继承、可见性和实例检查都只是该协议的应用约定。
t.equal(type(Counter), "table")
t.equal(rawget(instance, "add"), nil)

t.done()
