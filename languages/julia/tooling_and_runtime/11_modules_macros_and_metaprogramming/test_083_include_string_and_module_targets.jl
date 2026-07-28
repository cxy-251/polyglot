# polyglot-covers: julia.tooling.include-string-and-module-targets

using Test

@testset "include_string 在指定 module 的全局作用域求值" begin
    target = Module(:IncludeStringTarget)
    result = Base.include_string(target, "const value = 40\nvalue + 2\n", "virtual.jl")
    @test result == 42
    value = Base.invokelatest(getglobal, target, :value)
    @test value == 40
    @test !isdefined(Main, :value)
end
