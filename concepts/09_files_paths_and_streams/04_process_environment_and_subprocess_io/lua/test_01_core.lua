-- Common question: how are environment values, subprocess input/output, and exit status exposed?
-- Inputs: present/absent environment names, a successful pipe, and a nonzero shell exit.
-- Observations: optional string lookup, captured stdout, POSIX shell capability, and status tuple.
-- polyglot-family: files_paths_and_streams
-- polyglot-concept: process_environment_and_subprocess_io
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/
-- polyglot-related+: test_087_environment_files_and_subprocess_capabilities.lua

local t = require("support.assertions")

t.truth(os.getenv("PATH") == nil or type(os.getenv("PATH")) == "string")
t.equal(os.getenv("POLYGLOT_ENV_THAT_DOES_NOT_EXIST"), nil)

local pipe = assert(io.popen("printf 'stdout'", "r"))
t.equal(pipe:read("a"), "stdout")
local ok, reason, status = pipe:close()
t.truth(ok)
t.equal(reason, "exit")
t.equal(status, 0)

local failed, failed_reason, failed_status = os.execute("exit 9")
t.equal(failed, nil)
t.equal(failed_reason, "exit")
t.equal(failed_status, 9)

-- 环境继承和命令语法来自 host OS；Lua 没有环境 mutation 或 shell abstraction API。
t.done()
