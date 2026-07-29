-- Lua 课程与 harness 共用的最小断言库；它是测试基础设施，不计入课程知识。
local assertions = {}
local assertion_count = 0
local temporary_count = 0

local function fail(message, level)
    error(message, (level or 1) + 1)
end

local function inspect(value)
    if type(value) == "string" then
        return string.format("%q", value)
    end
    return tostring(value)
end

function assertions.equal(actual, expected, message)
    assertion_count = assertion_count + 1
    if actual ~= expected then
        fail(
            message or ("expected " .. inspect(expected) .. ", got " .. inspect(actual)),
            2
        )
    end
    return actual
end

function assertions.same(actual, expected, message)
    assertion_count = assertion_count + 1
    if not rawequal(actual, expected) then
        fail(
            message or ("expected identical " .. inspect(expected) .. ", got " .. inspect(actual)),
            2
        )
    end
    return actual
end

function assertions.truth(value, message)
    assertion_count = assertion_count + 1
    if not value then
        fail(message or ("expected truthy value, got " .. inspect(value)), 2)
    end
    return value
end

function assertions.falsey(value, message)
    assertion_count = assertion_count + 1
    if value then
        fail(message or ("expected false or nil, got " .. inspect(value)), 2)
    end
    return value
end

function assertions.near(actual, expected, tolerance, message)
    assertion_count = assertion_count + 1
    if math.abs(actual - expected) > tolerance then
        fail(
            message
                or string.format(
                    "expected %.17g within %.17g of %.17g",
                    actual,
                    tolerance,
                    expected
                ),
            2
        )
    end
    return actual
end

function assertions.matches(value, pattern, message)
    assertion_count = assertion_count + 1
    if type(value) ~= "string" or not string.find(value, pattern) then
        fail(message or ("expected " .. inspect(value) .. " to match " .. inspect(pattern)), 2)
    end
    return value
end

function assertions.raises(callback, fragment)
    local ok, raised = pcall(callback)
    assertion_count = assertion_count + 1
    if ok then
        fail("expected callback to raise an error", 2)
    end
    if fragment ~= nil and not string.find(tostring(raised), fragment, 1, true) then
        fail(
            "expected error containing " .. inspect(fragment) .. ", got " .. inspect(raised),
            2
        )
    end
    return raised
end

function assertions.pack_equal(actual, expected)
    assertions.equal(actual.n, expected.n, "packed result count differs")
    for index = 1, expected.n do
        assertions.equal(actual[index], expected[index], "packed result differs at " .. index)
    end
end

function assertions.with_cleanup(body, cleanup)
    local body_result = table.pack(xpcall(body, debug.traceback))
    local cleanup_result = table.pack(pcall(cleanup))
    if not cleanup_result[1] then
        error(cleanup_result[2], 0)
    end
    if not body_result[1] then
        error(body_result[2], 0)
    end
    return table.unpack(body_result, 2, body_result.n)
end

function assertions.temp_path(stem)
    local root = assert(os.getenv("POLYGLOT_LUA_TEST_TMP"), "isolated temp root is required")
    temporary_count = temporary_count + 1
    return string.format("%s/%02d-%s", root, temporary_count, stem or "fixture")
end

function assertions.done()
    if assertion_count == 0 then
        fail("test file did not execute any assertions", 2)
    end
    print(string.format("Lua assertions passed: %d", assertion_count))
end

return assertions
