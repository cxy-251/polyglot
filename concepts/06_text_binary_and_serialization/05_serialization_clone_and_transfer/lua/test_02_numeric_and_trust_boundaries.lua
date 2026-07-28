-- Common question: where do numeric fidelity, versioning, and trust constrain transfer formats?
-- Inputs: 64-bit integers, doubles, dumped bytecode, text-only loading, and hostile source.
-- Observations: exact integer packing, floating precision, binary mode gates, and executable-code risk.
-- polyglot-family: text_binary_and_serialization
-- polyglot-concept: serialization_clone_and_transfer
-- polyglot-related: languages/lua/tooling_and_runtime/14_standalone_and_bytecode/
-- polyglot-related+: test_108_bytecode_compilation_and_loading.lua

local t = require("support.assertions")

local integer = math.maxinteger
local bytes = string.pack("<jdn", integer, 0.1, 0.1)
local decoded_integer, double_value, native_value = string.unpack("<jdn", bytes)
t.equal(decoded_integer, integer)
t.equal(double_value, 0.1)
t.equal(native_value, 0.1)

local bytecode = string.dump(function() return 42 end, true)
t.equal(assert(load(bytecode, "trusted-local", "b"))(), 42)
t.equal(select(1, load(bytecode, "text-only", "t")), nil)

local marker = {value = false}
local source = "return function(mark) mark.value = true end"
assert(load(source, "source", "t"))()(marker)
t.truth(marker.value)

-- Source and bytecode are executable, not safe data formats; bytecode also lacks cross-version portability.
t.done()
