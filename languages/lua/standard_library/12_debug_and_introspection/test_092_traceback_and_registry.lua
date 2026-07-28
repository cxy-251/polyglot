-- polyglot-covers: lua.debug.traceback_and_registry

local t = require("support.assertions")

local function nested()
    return debug.traceback("marker", 1)
end
local traceback = nested()
t.matches(traceback, "marker")
t.matches(traceback, "stack traceback")
t.matches(traceback, "test_092")

local registry = debug.getregistry()
t.equal(type(registry), "table")
t.equal(type(registry._LOADED), "table")
t.same(registry._LOADED, package.loaded)

-- registry 属于 C API state 的共享内部表；普通模块不应把它当作应用级 namespace。
t.done()
