# polyglot-family: time_locale_and_runtime
# polyglot-concept: durations_clocks_and_monotonic_time
# polyglot-related: languages/julia/tooling_and_runtime/15_reflection_time_and_runtime_observations/
# polyglot-related+: test_119_monotonic_and_wall_clock_observations.jl
#
# 共同问题：duration 与 timestamp 是否同一类型；测量 elapsed time 应选哪种 clock。
# 对照观察：time_ns 提供单调观察；Dates.Period 保留单位，Month 不能伪装成固定毫秒数。

using Test
using Dates

@testset "clock 读数和 duration 单位保持分离" begin
    before = time_ns()
    after = time_ns()
    @test after >= before
    @test time() isa Float64
    @test Millisecond(1500) + Millisecond(500) == Second(2)
    @test Dates.value(Millisecond(1500)) == 1500
    @test canonicalize(Millisecond(120_000)) == Minute(2)
    @test Hour(1) != Millisecond(1)
    @test typeof(Month(1)) === Month
    @test_throws MethodError convert(Millisecond, Month(1))
end
