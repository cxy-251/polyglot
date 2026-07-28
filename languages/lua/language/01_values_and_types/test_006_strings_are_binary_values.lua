-- polyglot-covers: lua.values.strings_are_binary_values

local t = require("support.assertions")

local binary = "A\0B\255"
t.equal(#binary, 4)
t.equal(string.byte(binary, 2), 0)
t.equal(string.byte(binary, 4), 255)
t.equal(binary, string.char(65, 0, 66, 255))
t.equal(type(binary), "string")

-- rawequal 只证明值相等；字符串驻留和地址不是可移植的语言级承诺。
t.truth(rawequal("poly" .. "glot", "polyglot"))

t.done()
