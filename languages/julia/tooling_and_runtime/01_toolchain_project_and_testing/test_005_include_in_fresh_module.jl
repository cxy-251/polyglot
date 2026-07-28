# polyglot-covers: julia.toolchain.include-and-module-isolation

using Test

@testset "include 可把文件装入显式的新模块" begin
    mktempdir(prefix = "polyglot-julia-") do directory
        source_path = joinpath(directory, "answer.jl")
        write(source_path, "answer() = 42\n")
        sandbox = Module(:CourseIncludeSandbox, false, false)
        Base.include(sandbox, source_path)
        # Julia 1.12 的全局 binding 同样受 world age 约束；动态定义后采用稳定入口调用。
        answer_function = Base.invokelatest(getglobal, sandbox, :answer)
        @test Base.invokelatest(answer_function) == 42
        @test !isdefined(Main, :answer)
    end
end
