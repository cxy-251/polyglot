-- Common question: how do mapping lookup, missing keys, defaults, and insertion interact?
-- Inputs: present false, absent keys, nil assignment, rawget, and __index defaults.
-- Observations: absence encoding, deletion, non-mutating fallback, and raw bypass.
-- polyglot-family: collections_and_iteration
-- polyglot-concept: mapping_lookup_and_missing_keys
-- polyglot-related: languages/lua/language/06_metatables_and_objects/
-- polyglot-related+: test_041_index_newindex_and_raw_access.lua

local t = require("support.assertions")
local values = {present = false}

t.equal(values.present, false)
t.equal(values.missing, nil)
t.equal(rawget(values, "missing"), nil)

values.answer = 42
t.equal(values.answer, 42)
values.answer = nil
t.equal(values.answer, nil)

local defaults = setmetatable(values, {__index = function(_, key) return "<" .. key .. ">" end})
t.equal(defaults.missing, "<missing>")
t.equal(rawget(defaults, "missing"), nil)
t.equal(next(defaults), "present")

t.done()
