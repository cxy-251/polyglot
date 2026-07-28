# polyglot-covers: julia.tooling.find-package-and-source-identity

using Test

@testset "find_package 返回当前 load path 上包入口而不执行源码" begin
    source_path = Base.find_package("PolyglotJuliaCourse")
    @test source_path !== nothing
    @test endswith(source_path, "languages/julia/src/PolyglotJuliaCourse.jl")
    @test isfile(source_path)
    @test Base.find_package("PackageThatDoesNotExist") === nothing
end
