# polyglot-covers: julia.toolchain.project-toml-and-compat

using Test
using TOML

project_path = normpath(joinpath(@__DIR__, "..", "..", "Project.toml"))
project = TOML.parsefile(project_path)

@testset "Project.toml 声明包身份与 Julia 兼容版本" begin
    @test project["name"] == "PolyglotJuliaCourse"
    @test project["compat"]["julia"] == "1.12.6"
    @test project["targets"]["test"] == ["Test"]
    @test haskey(project["extras"], "Test")
end
