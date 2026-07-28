# polyglot-covers: julia.toolchain.isolated-depot-and-load-path

using Test

@testset "运行器隔离 depot 与代码加载路径" begin
    @test length(DEPOT_PATH) == 1
    @test DEPOT_PATH[1] == abspath(ENV["JULIA_DEPOT_PATH"])
    @test LOAD_PATH == ["@", "@stdlib"]
    @test !isempty(Base.active_project())
end
