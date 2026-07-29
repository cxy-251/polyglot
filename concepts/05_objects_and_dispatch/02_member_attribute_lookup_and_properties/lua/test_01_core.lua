-- Common question: how are stored fields, computed properties, and missing members resolved?
-- Inputs: raw fields, __index functions, __newindex validation, and raw operations.
-- Observations: lookup order, computed values, write interception, and bypass boundaries.
-- polyglot-family: objects_and_dispatch
-- polyglot-concept: member_attribute_lookup_and_properties
-- polyglot-related: languages/lua/language/06_metatables_and_objects/
-- polyglot-related+: test_041_index_newindex_and_raw_access.lua

local t = require("support.assertions")
local storage = {width = 6, height = 7}
local object = setmetatable({}, {
    __index = function(_, key)
        if key == "area" then return storage.width * storage.height end
        return storage[key]
    end,
    __newindex = function(_, key, value)
        assert(key == "width" or key == "height", "unknown property")
        storage[key] = value
    end,
})

t.equal(object.area, 42)
object.width = 7
t.equal(object.area, 49)
t.raises(function() object.other = 1 end, "unknown property")
t.equal(rawget(object, "area"), nil)
rawset(object, "area", 42)
t.equal(object.area, 42)

t.done()
