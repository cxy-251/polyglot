-- polyglot-covers: lua.modules.namespaces_and_environments

local t = require("support.assertions")
local module_environment = {}
local chunk = assert(load([[
    local module = {}
    function module.answer()
        return 42
    end
    accidental = "module environment only"
    return module
]], "module-environment", "t", module_environment))

local module = chunk()
t.equal(module.answer(), 42)
t.equal(module_environment.accidental, "module environment only")
t.equal(rawget(_G, "accidental"), nil)
t.equal(rawget(module, "accidental"), nil)

-- Lua module 通常显式返回 table；chunk 环境、返回 namespace 与 _G 是不同对象。
t.done()
