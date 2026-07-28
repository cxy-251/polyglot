-- polyglot-covers: lua.scope.shared_upvalues

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
t.equal(deposit(5), 90)

local first_id = debug.upvalueid(deposit, 1)
local second_id = debug.upvalueid(withdraw, 1)
t.equal(first_id, second_id)

t.done()
