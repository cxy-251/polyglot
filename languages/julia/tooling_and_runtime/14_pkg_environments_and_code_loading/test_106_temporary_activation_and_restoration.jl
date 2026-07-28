# polyglot-covers: julia.tooling.pkg-temporary-activation-and-restoration

using Test
using Pkg

@testset "Pkg.activate 切换显式环境，调用方负责恢复" begin
    original_project = Base.active_project()
    mktempdir(prefix = "polyglot-julia-") do directory
        try
            Pkg.activate(directory; io = devnull)
            @test dirname(Base.active_project()) == directory
            @test Pkg.project().name === nothing
        finally
            Pkg.activate(dirname(original_project); io = devnull)
        end
    end
    @test Base.active_project() == original_project
end
