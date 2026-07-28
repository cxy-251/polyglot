# polyglot-covers: julia.tooling.dependency-free-project-boundary

using Test
using Pkg
using TOML

@testset "普通课程项目没有第三方 dependency" begin
    project_path = Base.active_project()
    project = TOML.parsefile(project_path)
    @test !haskey(project, "deps")
    @test isempty(Pkg.project().dependencies)
    @test Set(keys(project["extras"])) == Set(["Test"])
    @test project["targets"]["test"] == ["Test"]
end
