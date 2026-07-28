-- polyglot-covers: lua.c_api.structured_data_and_capabilities

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("structured"), "C API case passed: structured")

local native = require("polyglot_native")
local record = native.record("answer", 42)
t.equal(record.label, "answer")
t.equal(record.value, 42)

-- 宿主用 table 传递结构化数据，并只注入明确的 C function 能力。
t.done()
