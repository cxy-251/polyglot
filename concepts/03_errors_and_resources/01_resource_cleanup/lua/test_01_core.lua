-- Common question: how is a successfully acquired resource released on every exit?
-- Inputs: normal return, raised error, a real file, and a to-be-closed wrapper.
-- Observations: __close invocation, error argument, closed state, and preserved body error.
-- polyglot-family: errors_and_resources
-- polyglot-concept: resource_cleanup
-- polyglot-related: languages/lua/language/07_errors_and_resources/test_055_file_cleanup_protocol.lua

local t = require("support.assertions")
local path = t.temp_path("cleanup.txt")
local file = assert(io.open(path, "w"))
local observed_error
local resource = setmetatable({file = file}, {
    __close = function(self, error_value)
        observed_error = error_value
        self.file:close()
    end,
})

local ok, error_value = pcall(function()
    local handle <close> = resource
    assert(handle.file:write("payload"))
    error("body failed")
end)
t.falsey(ok)
t.matches(error_value, "body failed")
t.same(observed_error, error_value)
t.equal(io.type(file), "closed file")
t.truth(os.remove(path))

t.done()
