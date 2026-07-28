# polyglot-family: time_locale_and_runtime
# polyglot-concept: durations_clocks_and_monotonic_time
# polyglot-related: languages/julia/tooling_and_runtime/15_reflection_time_and_runtime_observations/
# polyglot-related+: test_119_monotonic_and_wall_clock_observations.jl
#
# 共同问题：duration 与 timestamp 是否同一类型；测量 elapsed time 应选哪种 clock。
# 对照观察：time_ns 提供单调纳秒观察，time 是 wall-clock 秒；Dates.Period 表示带单位 duration。

using Test
using Dates

@testset "clock 读数和 duration 单位保持分离" begin
    before = time_ns()
    after = time_ns()
    @test after >= before
    @test time() isa Float64
    @test Millisecond(1500) + Millisecond(500) == Second(2)
    @test Dates.value(Millisecond(1500)) == 1500
end
