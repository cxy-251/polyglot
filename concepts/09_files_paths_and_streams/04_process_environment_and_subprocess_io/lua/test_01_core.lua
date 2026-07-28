-- Common question: how are environment values, subprocess input/output, and exit status exposed?
-- Inputs: isolated environment variables, a successful pipe, and a nonzero shell exit.
-- Observations: string lookup, inherited environment, captured stdout, and status tuple.
-- polyglot-family: files_paths_and_streams
-- polyglot-concept: process_environment_and_subprocess_io
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/test_088_subprocess_status_and_pipes.lua

local t = require("support.assertions")

t.equal(os.getenv("TZ"), "UTC")
t.equal(os.getenv("POLYGLOT_LUA_TEST_TMP"), os.getenv("TMPDIR"))
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

t.done()
