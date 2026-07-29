# polyglot-covers: julia.stdlib.test-and-logging-contracts

using Test
using Logging

function require_positive(value)
    value > 0 || throw(ArgumentError("value must be positive"))
    return value
end

@testset "Test 与 Logging 提供结构化成功、失败和诊断观察" begin
    @test require_positive(3) == 3
    @test_throws ArgumentError require_positive(0)
    @test 0.1 + 0.2 ≈ 0.3
    @test_logs (:warn, "fallback") @warn "fallback"
    @test_logs min_level = Logging.Error begin
        @info "filtered"
    end
end
