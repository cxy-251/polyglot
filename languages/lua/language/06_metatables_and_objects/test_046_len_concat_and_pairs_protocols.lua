-- polyglot-covers: lua.metatables.len_concat_and_pairs_protocols

local t = require("support.assertions")
local value = setmetatable({hidden = {alpha = 1, beta = 2}}, {
    __len = function(self)
        return 2
    end,
    __concat = function(left, right)
        return tostring(left.hidden.alpha) .. right
    end,
    __pairs = function(self)
        return next, self.hidden, nil
    end,
})

t.equal(#value, 2)
t.equal(value .. "!", "1!")

local copied = {}
for key, item in pairs(value) do
    copied[key] = item
end
t.equal(copied.alpha, 1)
t.equal(copied.beta, 2)
t.equal(rawget(value, "alpha"), nil)

t.done()
