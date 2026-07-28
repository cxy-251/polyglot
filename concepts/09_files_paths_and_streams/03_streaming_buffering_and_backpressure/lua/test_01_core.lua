-- Common question: how do streams chunk data, buffer writes, and signal backpressure?
-- Inputs: a buffered file, explicit flush, fixed-size reads, EOF, and a process pipe.
-- Observations: synchronous completion, byte chunks, nil EOF, explicit buffering, and no backpressure protocol.
-- polyglot-family: files_paths_and_streams
-- polyglot-concept: streaming_buffering_and_backpressure
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/
-- polyglot-related+: test_085_buffering_flush_and_temporary_files.lua

local t = require("support.assertions")
local file = assert(io.tmpfile())
t.truth(file:setvbuf("full", 64))
t.same(file:write("abcdef"), file)
t.truth(file:flush())
t.equal(file:seek("set", 0), 0)
t.equal(file:read(2), "ab")
t.equal(file:read(2), "cd")
t.equal(file:read(8), "ef")
t.equal(file:read(1), nil)
t.truth(file:close())

local pipe = assert(io.popen("printf 'chunk'", "r"))
t.equal(pipe:read(2), "ch")
t.equal(pipe:read("a"), "unk")
t.truth(pipe:close())

-- io 是阻塞式 file-handle API；没有标准 async stream、drain 或 backpressure signal。
t.done()
