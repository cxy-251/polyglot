# polyglot-covers: julia.toolchain.locked-version-and-project

using Test
using PolyglotJuliaCourse

@testset "锁定工具链与活动项目" begin
    @test VERSION == v"1.12.6"
    @test PolyglotJuliaCourse.locked_version() == VERSION
    @test endswith(Base.active_project(), "languages/julia/Project.toml")
    @test Base.isinteractive() === false
end
