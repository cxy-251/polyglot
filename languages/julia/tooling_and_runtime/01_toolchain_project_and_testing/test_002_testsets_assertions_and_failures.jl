# polyglot-covers: julia.toolchain.test-standard-library

using Test

function require_positive(value)
    value > 0 || throw(ArgumentError("value must be positive"))
    return value
end

@testset "Test 标准库表达成功与失败契约" begin
    @test require_positive(3) == 3
    @test_throws ArgumentError require_positive(0)
    @test 0.1 + 0.2 ≈ 0.3
end
