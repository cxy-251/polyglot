-- polyglot-covers: lua.debug.registry_metatable_and_privilege_boundaries

local t = require("support.assertions")
local hidden = {__metatable = "sealed", answer = 42}
local value = setmetatable({}, hidden)
t.equal(getmetatable(value), "sealed")
t.same(debug.getmetatable(value), hidden)

local replacement = {__index = {answer = 43}}
t.same(debug.setmetatable(value, replacement), value)
t.equal(value.answer, 43)
debug.setmetatable(value, hidden)
t.equal(getmetatable(value), "sealed")

local registry = debug.getregistry()
t.equal(type(registry), "table")
t.equal(type(registry._LOADED), "table")
t.same(registry._LOADED, package.loaded)

-- debug 可越过 metatable 保护并暴露 registry；普通模块不应把这些能力当作封装 API。
t.done()
