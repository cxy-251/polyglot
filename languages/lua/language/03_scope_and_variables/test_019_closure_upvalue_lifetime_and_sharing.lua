-- polyglot-covers: lua.scope.closure_upvalue_lifetime_and_sharing

local t = require("support.assertions")

local function account(opening)
    local balance = opening
    local function deposit(amount)
        balance = balance + amount
        return balance
    end
    local function withdraw(amount)
        balance = balance - amount
        return balance
    end
    return deposit, withdraw
end

local deposit, withdraw = account(100)
t.equal(deposit(25), 125)
t.equal(withdraw(40), 85)

-- 闭包维持捕获变量的生命周期；两个返回函数共享同一个变量而非值快照。
collectgarbage("collect")
t.equal(deposit(5), 90)

local separate_deposit = account(100)
t.equal(separate_deposit(1), 101)
t.equal(deposit(1), 91)

t.done()
