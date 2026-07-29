# polyglot-covers: julia.tooling.load-path-expansion-and-stdlib

using Test

@testset "LOAD_PATH 先解析活动项目，再显式回退到标准库" begin
    original_load_path = copy(LOAD_PATH)
    mktempdir(prefix = "polyglot-julia-") do directory
        write(joinpath(directory, "Project.toml"), "[deps]\n")
        try
            pushfirst!(LOAD_PATH, directory)
            expanded = Base.load_path()
            @test first(expanded) == joinpath(directory, "Project.toml")
            @test Base.active_project() in expanded
            @test Base.find_package("Test") !== nothing
        finally
            empty!(LOAD_PATH)
            append!(LOAD_PATH, original_load_path)
        end
    end
    @test LOAD_PATH == original_load_path
end
