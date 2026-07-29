# polyglot-covers: julia.tooling.pkg-offline-resolution-and-status

using Test
using Pkg
using TOML

@testset "空环境可离线 resolve，status 只描述当前环境" begin
    original_project = Base.active_project()
    mktempdir(prefix = "polyglot-julia-") do directory
        try
            write(joinpath(directory, "Project.toml"), "[deps]\n")
            Pkg.activate(directory; io = devnull)
            Pkg.offline(true)
            Pkg.resolve(; io = devnull)
            manifest = TOML.parsefile(joinpath(directory, "Manifest.toml"))
            @test manifest["manifest_format"] == "2.0"
            @test VersionNumber(manifest["julia_version"]) == VERSION
            output = IOBuffer()
            Pkg.status(; io = output)
            @test occursin("empty project", String(take!(output)))
        finally
            Pkg.offline(false)
            Pkg.activate(dirname(original_project); io = devnull)
        end
    end
    @test Base.active_project() == original_project
end
