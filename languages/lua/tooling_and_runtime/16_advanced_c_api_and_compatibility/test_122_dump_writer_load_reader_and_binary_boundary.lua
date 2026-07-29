-- polyglot-covers: lua.c_api.dump_writer_load_reader_and_binary_boundary

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("dump-load"), "C API case passed: dump%-load")

-- lua_dump 不弹出函数。5.5 writer 在数据结束后收到一次 NULL/0；
-- lua_load reader 分块返回数据。两侧都必须处理失败，且 binary chunk 仅限兼容构建。
t.done()
