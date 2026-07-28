-- polyglot-covers: lua.modules.c_module_loading

local t = require("support.assertions")
package.loaded.polyglot_native = nil

local native, loader_path = require("polyglot_native")
t.equal(native.add(19, 23), 42)
t.equal(type(loader_path), "string")
t.matches(loader_path, "polyglot_native%.so")
t.same(package.loaded.polyglot_native, native)

local searcher = package.searchers[3]
local loader, data = searcher("polyglot_native")
t.equal(type(loader), "function")
t.matches(data, "polyglot_native%.so")

-- 动态模块由锁定解释器导出的 Lua C API 符号解析，不使用 LuaRocks 或系统 module。
t.done()
