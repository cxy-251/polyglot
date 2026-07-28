# polyglot-covers: julia.runtime.lowered-and-typed-code-observations

using Test
using InteractiveUtils

runtime_double(value::Int) = value * 2

@testset "compiler reflection 只检查结构，不锁定文本和具体优化" begin
    lowered = code_lowered(runtime_double, (Int,))
    typed = code_typed(runtime_double, (Int,); optimize = false)
    @test length(lowered) == 1
    @test first(lowered) isa Core.CodeInfo
    @test length(typed) == 1
    @test last(first(typed)) === Int
end
