# polyglot-covers: julia.tooling.pkg-project-and-active-environment

using Test
using Pkg

@testset "Pkg.project 与 Base.active_project 描述当前显式环境" begin
    project = Pkg.project()
    @test project.name == "PolyglotJuliaCourse"
    @test project.version == v"0.1.0"
    @test project.ispackage
    @test endswith(Base.active_project(), "languages/julia/Project.toml")
end
