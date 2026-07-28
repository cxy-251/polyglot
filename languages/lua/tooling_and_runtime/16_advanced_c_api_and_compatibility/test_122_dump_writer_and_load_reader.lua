-- polyglot-covers: lua.c_api.dump_writer_and_load_reader

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("dump-load"), "C API case passed: dump%-load")

-- Lua 5.5 lua_dump 最后以 NULL/0 再调用 writer；binary chunk 仍只限兼容构建。
t.done()
