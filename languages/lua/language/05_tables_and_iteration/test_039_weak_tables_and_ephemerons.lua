-- polyglot-covers: lua.tables.weak_tables_and_ephemerons

local t = require("support.assertions")

local weak_values = setmetatable({}, {__mode = "v"})
do
    local value = {}
    weak_values.item = value
    t.same(weak_values.item, value)
end

for _ = 1, 20 do
    collectgarbage("collect")
    if weak_values.item == nil then
        break
    end
end
t.equal(weak_values.item, nil)

local ephemeron = setmetatable({}, {__mode = "k"})
do
    local key = {}
    ephemeron[key] = {back_reference = key}
end
for _ = 1, 20 do
    collectgarbage("collect")
    if next(ephemeron) == nil then
        break
    end
end
t.equal(next(ephemeron), nil)

t.done()
