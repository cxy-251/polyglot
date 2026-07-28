-- polyglot-covers: lua.tables.next_pairs_and_unspecified_order

local t = require("support.assertions")

local source = {alpha = 1, beta = 2, gamma = 3}
local observed = {}
for key, value in pairs(source) do
    observed[key] = value
end

t.equal(observed.alpha, 1)
t.equal(observed.beta, 2)
t.equal(observed.gamma, 3)

local count = 0
local key = nil
repeat
    key = next(source, key)
    if key ~= nil then
        count = count + 1
    end
until key == nil
t.equal(count, 3)

-- pairs/next 的遍历顺序未指定，因此只断言成员，不锁定当前哈希布局。
t.done()
