-- polyglot-covers: lua.luac.syntax_and_listing

local t = require("support.assertions")
local source_path = t.temp_path("compile.lua")
local listing_path = t.temp_path("compile.list")
local file = assert(io.open(source_path, "w"))
assert(file:write("local value = 6 * 7\nreturn value\n"))
assert(file:close())

t.truth(os.execute(string.format("luac -p %q", source_path)))
t.truth(os.execute(string.format("luac -l -p %q > %q", source_path, listing_path)))

local listing = assert(io.open(listing_path, "r"))
local content = listing:read("a")
t.truth(listing:close())
t.matches(content, "main")
t.matches(content, "RETURN")

t.truth(os.remove(source_path))
t.truth(os.remove(listing_path))
t.done()
