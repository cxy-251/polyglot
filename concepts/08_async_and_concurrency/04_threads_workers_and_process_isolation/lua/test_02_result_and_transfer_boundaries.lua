-- Common question: how do isolated workers transfer results and failures?
-- Inputs: an isolated C state, binary scalar encoding, tables, functions, and userdata.
-- Observations: host-mediated state isolation, explicit value encoding, and non-transferable identities.
-- polyglot-family: async_and_concurrency
-- polyglot-concept: threads_workers_and_process_isolation
-- polyglot-related: languages/lua/tooling_and_runtime/16_advanced_c_api_and_compatibility/
-- polyglot-related+: test_124_structured_data_and_capabilities.lua

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("structured"), "C API case passed: structured")

local encoded = string.pack("<i8", 42)
local decoded = string.unpack("<i8", encoded)
t.equal(decoded, 42)

local table_value = {answer = 42}
local function_value = function() return 42 end
local userdata_value = io.tmpfile()
t.equal(type(table_value), "table")
t.equal(type(function_value), "function")
t.equal(type(userdata_value), "userdata")
t.truth(userdata_value:close())

-- Table/function/userdata identity cannot be moved between independent states by a standard Lua API.
t.done()
