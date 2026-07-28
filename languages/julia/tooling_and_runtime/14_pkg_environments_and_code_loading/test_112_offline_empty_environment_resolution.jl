# polyglot-covers: julia.tooling.offline-empty-environment-resolution

using Test
using Pkg
using TOML

@testset "空环境可在 offline 模式 resolve 而不访问 registry 或网络" begin
    original_project = Base.active_project()
    mktempdir(prefix = "polyglot-julia-") do directory
        try
            write(joinpath(directory, "Project.toml"), "[deps]\n")
            Pkg.activate(directory; io = devnull)
            Pkg.offline(true)
            Pkg.resolve(; io = devnull)
            manifest_path = joinpath(directory, "Manifest.toml")
            @test isfile(manifest_path)
            manifest = TOML.parsefile(manifest_path)
            @test manifest["julia_version"] == "1.12.6"
            @test manifest["manifest_format"] == "2.0"
        finally
            Pkg.activate(dirname(original_project); io = devnull)
        end
    end
end
