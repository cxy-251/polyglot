-- Common question: how do value equality, identity, and custom equality differ?
-- Inputs: integer/float values, strings, distinct tables, aliases, and metatables.
-- Observations: ==, rawequal, numeric subtype equality, and __eq dispatch.
-- polyglot-family: values_and_comparison
-- polyglot-concept: equality
-- polyglot-related: languages/lua/language/06_metatables_and_objects/test_045_equality_and_order_metamethods.lua

local t = require("support.assertions")

t.truth(3 == 3.0)
t.truth(rawequal(3, 3.0))
t.truth("lua" == ("lu" .. "a"))

local first = {}
local alias = first
local distinct = {}
t.truth(first == alias)
t.falsey(first == distinct)

local by_key = {__eq = function(left, right) return left.key == right.key end}
local left = setmetatable({key = 1}, by_key)
local right = setmetatable({key = 1}, by_key)
t.truth(left == right)
t.falsey(rawequal(left, right))

t.done()
