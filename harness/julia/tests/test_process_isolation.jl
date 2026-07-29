using Test
using Base.Threads

@testset "Julia runner 隔离进程状态与线程配置" begin
    @test length(DEPOT_PATH) == 1
    @test DEPOT_PATH[1] == abspath(ENV["JULIA_DEPOT_PATH"])
    @test LOAD_PATH == ["@", "@stdlib"]
    @test Base.active_project() in Base.load_path()
    @test Base.isinteractive() === false
    @test nthreads(:default) == 2
    @test nthreads(:interactive) == 0
    @test threadpool() === :default
end
