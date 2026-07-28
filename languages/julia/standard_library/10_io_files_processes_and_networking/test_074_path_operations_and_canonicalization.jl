# polyglot-covers: julia.stdlib.path-operations-and-canonicalization

using Test

@testset "词法路径处理与文件系统 canonicalization 是不同操作" begin
    @test normpath(joinpath("a", "..", "b", ".")) == joinpath("b", "")
    @test basename(joinpath("a", "value.txt")) == "value.txt"
    @test dirname(joinpath("a", "value.txt")) == "a"
    mktempdir(prefix = "polyglot-julia-") do directory
        path = joinpath(directory, "value.txt")
        write(path, "value")
        @test realpath(path) == abspath(path)
        @test ispath(path)
    end
end
