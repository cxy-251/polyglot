# polyglot-covers: julia.tooling.load-path-expansion-and-stdlib

using Test

@testset "LOAD_PATH 先解析活动项目，再显式回退到标准库" begin
    expanded = Base.load_path()
    @test LOAD_PATH == ["@", "@stdlib"]
    @test first(expanded) == Base.active_project()
    @test any(path -> endswith(path, "share/julia/stdlib/v1.12"), expanded)
    @test Base.find_package("Test") !== nothing
end
