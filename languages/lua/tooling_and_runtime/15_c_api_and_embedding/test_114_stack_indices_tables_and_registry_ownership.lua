-- polyglot-covers: lua.c_api.stack_indices_tables_and_registry_ownership

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("stack"), "C API case passed: stack")
t.matches(c_api.run("tables-registry"), "C API case passed: tables%-registry")

-- C API 使用虚拟栈传参和返回：正/负索引、pseudo-index 与 acceptable index 含义不同。
-- lua_tolstring 指针只在值保持可达且未发生使其失效的 API 操作时有效。
-- registry reference 属于创建它的 state，必须用同一 registry 的 luaL_unref 成对释放。
t.done()
