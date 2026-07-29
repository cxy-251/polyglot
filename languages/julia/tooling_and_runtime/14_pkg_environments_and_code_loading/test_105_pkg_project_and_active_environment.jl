# polyglot-covers: julia.tooling.pkg-environment-activation-and-restoration

using Test
using Pkg

@testset "Pkg.activate 切换显式环境，调用方负责恢复" begin
    original_project = Base.active_project()
    remembered_project = Ref("")
    mktempdir(prefix = "polyglot-julia-") do directory
        try
            Pkg.activate(directory; io = devnull)
            remembered_project[] = Base.active_project()
            @test dirname(remembered_project[]) == directory
            @test Pkg.project().name === nothing
            @test isempty(Pkg.project().dependencies)
        finally
            Pkg.activate(dirname(original_project); io = devnull)
        end
    end
    @test Base.active_project() == original_project
    @test !ispath(dirname(remembered_project[]))
end
