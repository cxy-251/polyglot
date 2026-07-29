using Test
using TOML

fixture = normpath(joinpath(@__DIR__, "..", "fixture", "PolyglotJuliaHarnessFixture"))
project = TOML.parsefile(joinpath(fixture, "Project.toml"))

@testset "Julia harness 锁定工具链与本地工程" begin
    @test VERSION == v"1.12.6"
    @test project["name"] == "PolyglotJuliaHarnessFixture"
    @test project["compat"]["julia"] == "1.12.6"
    @test !haskey(project, "deps")
    @test project["targets"]["test"] == ["Test"]
    @test isfile(joinpath(fixture, "src", "PolyglotJuliaHarnessFixture.jl"))
end
