-- polyglot-covers: lua.runtime.version_and_configuration

local t = require("support.assertions")

t.equal(_VERSION, "Lua 5.5")
t.equal(math.type(1), "integer")
t.equal(math.type(1.0), "float")
t.equal(string.packsize("j"), 8)
t.equal(string.packsize("n"), 8)
t.equal(package.config:sub(1, 1), "/")

local lua_path = assert(io.popen("command -v lua", "r"))
t.equal(lua_path:read("l"), "/usr/local/bin/lua")
t.truth(lua_path:close())

local luac_path = assert(io.popen("command -v luac", "r"))
t.equal(luac_path:read("l"), "/usr/local/bin/luac")
t.truth(luac_path:close())

t.done()
