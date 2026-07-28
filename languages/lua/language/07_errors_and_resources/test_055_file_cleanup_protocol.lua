-- polyglot-covers: lua.resources.file_cleanup_protocol

local t = require("support.assertions")
local path = t.temp_path("resource.txt")

local resource = assert(io.open(path, "w+"))
local guarded = setmetatable({file = resource}, {
    __close = function(self)
        self.file:close()
    end,
})

local ok = pcall(function()
    local handle <close> = guarded
    assert(handle.file:write("payload"))
    error("stop after write")
end)
t.falsey(ok)
t.equal(io.type(resource), "closed file")

local reader = assert(io.open(path, "r"))
t.equal(reader:read("a"), "payload")
t.truth(reader:close())
t.truth(os.remove(path))

t.done()
