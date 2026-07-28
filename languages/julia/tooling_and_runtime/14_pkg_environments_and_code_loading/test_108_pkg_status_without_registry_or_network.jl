# polyglot-covers: julia.tooling.pkg-status-without-network

using Test
using Pkg

@testset "Pkg.status 可只读取活动项目而不解析或下载依赖" begin
    output = IOBuffer()
    Pkg.status(; io = output)
    rendered = String(take!(output))
    @test occursin("PolyglotJuliaCourse", rendered)
    @test isempty(Pkg.project().dependencies)
    @test !occursin("Downloading", rendered)
end
