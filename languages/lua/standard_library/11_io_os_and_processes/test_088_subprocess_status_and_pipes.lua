-- polyglot-covers: lua.os.subprocess_status_and_pipes

local t = require("support.assertions")

local ok, reason, status = os.execute("exit 0")
t.truth(ok)
t.equal(reason, "exit")
t.equal(status, 0)

local failed, failed_reason, failed_status = os.execute("exit 7")
t.equal(failed, nil)
t.equal(failed_reason, "exit")
t.equal(failed_status, 7)

local pipe = assert(io.popen("printf 'lua-process'", "r"))
t.equal(pipe:read("a"), "lua-process")
local pipe_ok, pipe_reason, pipe_status = pipe:close()
t.truth(pipe_ok)
t.equal(pipe_reason, "exit")
t.equal(pipe_status, 0)

t.done()
