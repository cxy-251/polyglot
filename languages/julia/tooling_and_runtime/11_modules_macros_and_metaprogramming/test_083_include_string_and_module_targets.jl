# polyglot-covers: julia.tooling.include-eval-and-module-targets

using Test

@testset "include、include_string 与 eval 都在显式 module global scope 求值" begin
    mktempdir(prefix = "polyglot-julia-") do directory
        source_path = joinpath(directory, "answer.jl")
        write(source_path, "answer() = 42\n")
        target = Module(:CourseIncludeTarget)
        Base.include(target, source_path)
        answer = Base.invokelatest(getglobal, target, :answer)
        @test Base.invokelatest(answer) == 42
        result = Base.include_string(target, "const value = 40\nvalue + 2\n", "virtual.jl")
        @test result == 42
        @test Base.invokelatest(getglobal, target, :value) == 40
        Core.eval(target, :(const evaluated = value + 2))
        @test Base.invokelatest(getglobal, target, :evaluated) == 42
        @test !isdefined(Main, :answer)
        @test !isdefined(Main, :value)
    end
end
