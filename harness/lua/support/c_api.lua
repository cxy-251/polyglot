-- C API fixture 进程适配器属于 harness；课程只讨论它验证的公开 API 契约。
local c_api = {}

function c_api.run(case_name)
    local host = assert(
        os.getenv("POLYGLOT_LUA_C_API_HOST"),
        "POLYGLOT_LUA_C_API_HOST is required"
    )
    local command = string.format("%q %q 2>&1", host, case_name)
    local pipe = assert(io.popen(command, "r"))
    local output = pipe:read("a")
    local ok, reason, status = pipe:close()
    if not ok then
        error(
            string.format(
                "C API case %s failed (%s %s):\n%s",
                case_name,
                tostring(reason),
                tostring(status),
                output
            ),
            2
        )
    end
    return output
end

return c_api
