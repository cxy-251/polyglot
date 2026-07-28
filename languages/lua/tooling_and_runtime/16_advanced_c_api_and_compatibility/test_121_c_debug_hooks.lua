-- polyglot-covers: lua.c_api.debug_hooks

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("hook"), "C API case passed: hook")

-- count hook 以指令计数建立确定条件，并在断言前撤销，不依赖墙钟或 sleep。
t.done()
