-- Common question: how are relative paths, separators, normalization, and resolution handled?
-- Inputs: current directory, dot segments, package.config, and equivalent file spellings.
-- Observations: process-cwd resolution, platform separator, OS interpretation, and absent path library.
-- polyglot-family: files_paths_and_streams
-- polyglot-concept: path_normalization_and_resolution
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/
-- polyglot-related+: test_087_environment_files_and_subprocess_capabilities.lua

local t = require("support.assertions")
local root = assert(os.getenv("POLYGLOT_LUA_TEST_TMP"))
local separator = package.config:sub(1, 1)
local path = root .. separator .. "path.txt"
local file = assert(io.open(path, "w"))
assert(file:write("payload"))
assert(file:close())

local dotted = root .. separator .. "." .. separator .. "path.txt"
local reader = assert(io.open(dotted, "r"))
t.equal(reader:read("a"), "payload")
t.truth(reader:close())
t.equal(type(separator), "string")
t.equal(#separator, 1)
t.equal(rawget(os, "realpath"), nil)
t.equal(rawget(os, "path"), nil)
t.truth(os.remove(path))

-- `.` 的解释和 separator 来自 OS；Lua 只传递字符串，不提供 normalize/resolve/path object。
t.done()
