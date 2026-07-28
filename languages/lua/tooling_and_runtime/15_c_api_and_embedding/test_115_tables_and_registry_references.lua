-- polyglot-covers: lua.c_api.tables_and_registry_references

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(
    c_api.run("tables-registry"),
    "C API case passed: tables%-registry"
)

-- registry 属于 state，不等同 _G；luaL_ref 的引用必须由同一 registry 中的 luaL_unref 释放。
t.done()
