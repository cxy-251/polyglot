-- Common question: how are relative paths, separators, normalization, and resolution handled?
-- Inputs: current directory, dot segments, package.config, and equivalent file spellings.
-- Observations: process-cwd resolution, platform separator, OS interpretation, and absent path library.
-- polyglot-family: files_paths_and_streams
-- polyglot-concept: path_normalization_and_resolution
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/test_087_environment_rename_and_remove.lua

local t = require("support.assertions")
local root = assert(os.getenv("POLYGLOT_LUA_TEST_TMP"))
local path = root .. "/path.txt"
local file = assert(io.open(path, "w"))
assert(file:write("payload"))
assert(file:close())

local dotted = root .. "/./path.txt"
local reader = assert(io.open(dotted, "r"))
t.equal(reader:read("a"), "payload")
t.truth(reader:close())
t.equal(package.config:sub(1, 1), "/")
t.equal(rawget(os, "realpath"), nil)
t.equal(rawget(os, "path"), nil)
t.truth(os.remove(path))

-- Lua 标准库把 path 作为字符串交给 OS，不提供 normalize/resolve/path object。
t.done()
