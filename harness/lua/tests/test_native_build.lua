local t = require("support.assertions")
local c_api = require("support.c_api")
local native = require("polyglot_native")

t.equal(native.release, "Lua 5.5.0")
t.equal(native.add(20, 22), 42)
t.matches(c_api.run("state"), "C API case passed: state")
t.matches(c_api.run("version-gc"), "C API case passed: version%-gc")

-- 该测试证明锁定头文件、liblua、宿主和动态模块能够一起严格构建并执行。
t.done()
