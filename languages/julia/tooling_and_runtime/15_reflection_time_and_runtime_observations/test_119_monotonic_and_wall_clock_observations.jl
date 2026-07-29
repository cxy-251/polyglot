# polyglot-covers: julia.runtime.monotonic-and-wall-clock-observations

using Test

@testset "time_ns 用于单调间隔，time 返回 wall clock 秒数" begin
    before = time_ns()
    value = sum(1:100)
    after = time_ns()
    @test value == 5050
    @test after >= before
    @test time_ns() >= after
    @test typeof(before) === UInt64
    # wall clock 可跳变；只有 time_ns 的间隔用途是单调观察，不能推断调度或性能。
end
