-- Common question: how are files, directories, metadata, and symbolic links observed?
-- Inputs: a temporary directory, regular file, symbolic link, rename, and deletion.
-- Observations: I/O through a link, command exit status, rename/remove, and missing stat API.
-- polyglot-family: files_paths_and_streams
-- polyglot-concept: file_directory_metadata_and_links
-- polyglot-related: languages/lua/standard_library/11_io_os_and_processes/test_087_environment_rename_and_remove.lua

local t = require("support.assertions")
local root = assert(os.getenv("POLYGLOT_LUA_TEST_TMP"))
local directory = root .. "/files"
local source = directory .. "/source.txt"
local link = directory .. "/link.txt"
local renamed = directory .. "/renamed.txt"

t.truth(os.execute(string.format("mkdir %q", directory)))
local file = assert(io.open(source, "w"))
assert(file:write("payload"))
assert(file:close())
t.truth(os.execute(string.format("ln -s %q %q", source, link)))

local through_link = assert(io.open(link, "r"))
t.equal(through_link:read("a"), "payload")
t.truth(through_link:close())
t.truth(os.rename(source, renamed))
t.equal(io.open(link, "r"), nil)

t.truth(os.remove(link))
t.truth(os.remove(renamed))
t.truth(os.execute(string.format("rmdir %q", directory)))
t.equal(rawget(os, "stat"), nil)

t.done()
