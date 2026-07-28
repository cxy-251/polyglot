-- Common question: how are values formatted, parsed, and embedded into text?
-- Inputs: integers, floats, quoted text, bases, invalid text, and concatenation.
-- Observations: string.format, round-trip quoting, tonumber, explicit conversion, and no interpolation syntax.
-- polyglot-family: text_binary_and_serialization
-- polyglot-concept: formatting_parsing_and_interpolation
-- polyglot-related: languages/lua/standard_library/09_strings_patterns_utf8/test_071_format_and_dumped_functions.lua

local t = require("support.assertions")

t.equal(string.format("%04d", 42), "0042")
t.equal(string.format("%.2f", 1.25), "1.25")
t.equal(string.format("%x", 255), "ff")

local source = string.format("%q", "a\nb")
t.equal(assert(load("return " .. source, "quoted", "t"))(), "a\nb")
t.equal(tonumber("101010", 2), 42)
t.equal(tonumber("bad"), nil)

local name, value = "answer", 42
t.equal(name .. "=" .. tostring(value), "answer=42")

t.done()
