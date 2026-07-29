local t = require("support.assertions")

t.equal(_VERSION, "Lua 5.5")
t.equal(math.type(1), "integer")
t.equal(math.type(1.0), "float")
t.equal(string.packsize("j"), 8)
t.equal(string.packsize("n"), 8)

local lua = assert(io.popen("lua -E -v 2>&1", "r"))
t.matches(lua:read("a"), "Lua 5%.5%.0")
t.truth(lua:close())

local luac = assert(io.popen("luac -v 2>&1", "r"))
t.matches(luac:read("a"), "Lua 5%.5%.0")
t.truth(luac:close())

-- 精确 release、数值宽度和工具链配对是仓库运行合同，不是可移植 Lua 语义。
t.done()
