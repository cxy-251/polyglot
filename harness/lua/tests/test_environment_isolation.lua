local t = require("support.assertions")

for _, name in ipairs({
    "LUA_INIT",
    "LUA_INIT_5_5",
    "LUA_PATH",
    "LUA_PATH_5_5",
    "LUA_CPATH",
    "LUA_CPATH_5_5",
}) do
    t.equal(os.getenv(name), nil)
end

local home = assert(os.getenv("HOME"))
local temporary = assert(os.getenv("POLYGLOT_LUA_TEST_TMP"))
t.truth(home:match("/home$") ~= nil)
t.same(temporary, assert(os.getenv("TMPDIR")))
t.matches(package.path, "harness/lua")
t.falsey(package.path:match("%.luarocks"))

-- 每个文件运行在新进程中；真实用户启动脚本、module path 和持久目录都不可见。
t.done()
