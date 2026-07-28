-- polyglot-covers: lua.scope.global_declarations

local t = require("support.assertions")

local environment = {}
local declared = assert(load([[
    global answer
    answer = 42
    return answer
]], "declared-global", "t", environment))

t.equal(declared(), 42)
t.equal(environment.answer, 42)

local function compile(source)
    local chunk, message = load(source, "global-rules", "t", {})
    return chunk, message
end

local invalid, message = compile([[
    global allowed
    allowed = 1
    undeclared = 2
]])
t.equal(invalid, nil)
t.matches(message, "undeclared")

local read_only = assert(compile([[
    global<const> *
    return math
]]))
t.equal(read_only(), nil)

t.done()
