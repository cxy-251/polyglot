# polyglot-covers: julia.tooling.local-package-resolution-and-identity

using Test
using Pkg
using UUIDs

@testset "本地 develop 将源码身份接入环境，find_package 本身不执行模块" begin
    original_project = Base.active_project()
    package_uuid = UUID("e6970270-7d25-4e75-bf6a-47b9f8c95a21")
    mktempdir(prefix = "polyglot-julia-") do directory
        package = joinpath(directory, "CourseLocalPackage")
        environment = joinpath(directory, "environment")
        mkpath(joinpath(package, "src"))
        write(
            joinpath(package, "Project.toml"),
            """
            name = "CourseLocalPackage"
            uuid = "$package_uuid"
            version = "0.1.0"
            """,
        )
        write(
            joinpath(package, "src", "CourseLocalPackage.jl"),
            "module CourseLocalPackage\nanswer() = 42\nend\n",
        )
        try
            Pkg.activate(environment; io = devnull)
            Pkg.offline(true)
            Pkg.develop(path = package; io = devnull)
            source_path = Base.find_package("CourseLocalPackage")
            @test source_path == joinpath(package, "src", "CourseLocalPackage.jl")
            @test !isdefined(Main, :CourseLocalPackage)
            package_id = Base.PkgId(package_uuid, "CourseLocalPackage")
            loaded = Base.require(package_id)
            @test Base.PkgId(loaded) == package_id
            @test Base.invokelatest(getproperty(loaded, :answer)) == 42
        finally
            Pkg.offline(false)
            Pkg.activate(dirname(original_project); io = devnull)
        end
    end
end
