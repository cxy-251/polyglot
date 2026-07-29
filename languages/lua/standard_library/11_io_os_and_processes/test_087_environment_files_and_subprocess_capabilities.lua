-- polyglot-covers: lua.os.environment_files_and_subprocess_capabilities

local t = require("support.assertions")
local source = t.temp_path("source.txt")
local destination = t.temp_path("destination.txt")
local writer = assert(io.open(source, "w"))
assert(writer:write("payload"))
assert(writer:close())

local path_value = os.getenv("PATH")
t.truth(path_value == nil or type(path_value) == "string")
t.truth(os.rename(source, destination))
local reader = assert(io.open(destination, "r"))
t.equal(reader:read("a"), "payload")
t.truth(reader:close())
t.truth(os.remove(destination))
local removed, message = os.remove(destination)
t.equal(removed, nil)
t.equal(type(message), "string")

-- 命令文本由平台 shell 解释；以下是锁定 POSIX 环境的实现观察，不是可移植 Lua 语法。
local shell_available = os.execute()
t.equal(type(shell_available), "boolean")
if shell_available then
    local ok, reason, status = os.execute("exit 7")
    t.equal(ok, nil)
    t.equal(reason, "exit")
    t.equal(status, 7)

    local pipe = assert(io.popen("printf 'lua-process'", "r"))
    t.equal(pipe:read("a"), "lua-process")
    local pipe_ok, pipe_reason, pipe_status = pipe:close()
    t.truth(pipe_ok)
    t.equal(pipe_reason, "exit")
    t.equal(pipe_status, 0)
end

t.done()
