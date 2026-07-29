-- polyglot-covers: lua.modules.searchpath_templates

local t = require("support.assertions")
local root = t.temp_path("search-root")
local path = root .. "/?.lua;" .. root .. "/?/init.lua"

local module_directory = root .. "/nested"
t.truth(os.execute(string.format("mkdir -p %q", module_directory)))
local file = assert(io.open(module_directory .. "/module.lua", "w"))
assert(file:write("return true\n"))
assert(file:close())

local found = assert(package.searchpath("nested.module", path))
t.equal(found, module_directory .. "/module.lua")

local missing, message = package.searchpath("absent.module", path)
t.equal(missing, nil)
t.matches(message, "absent/module%.lua")

t.truth(os.remove(module_directory .. "/module.lua"))
t.truth(os.execute(string.format("rmdir %q", module_directory)))
t.truth(os.execute(string.format("rmdir %q", root)))

t.done()
