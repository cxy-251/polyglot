# polyglot-covers: julia.runtime.monotonic-and-wall-clock-observations

using Test

@testset "time_ns 用于单调间隔，time 返回 wall clock 秒数" begin
    before = time_ns()
    value = sum(1:100)
    after = time_ns()
    @test value == 5050
    @test after >= before
    @test time() > 0
    @test time_ns() >= after
end
