-- polyglot-covers: lua.modules.c_module_loading

local t = require("support.assertions")
package.loaded.polyglot_native = nil

local native, loader_path = require("polyglot_native")
t.equal(native.add(19, 23), 42)
t.equal(type(loader_path), "string")
t.matches(loader_path, "polyglot_native")
t.same(package.loaded.polyglot_native, native)

local searcher = package.searchers[3]
local loader, data = searcher("polyglot_native")
t.equal(type(loader), "function")
t.matches(data, "polyglot_native")

-- 动态库后缀和链接方式由平台决定；require 只依赖 package.cpath 与 luaopen_* 入口。
t.done()
