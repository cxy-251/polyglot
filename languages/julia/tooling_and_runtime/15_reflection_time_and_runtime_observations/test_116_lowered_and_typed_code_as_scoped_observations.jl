# polyglot-covers: julia.runtime.compiler-and-memory-observations

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
    values = [1, 2, 3]
    payload_bytes = sizeof(Int) * length(values)
    @test sizeof(values) == payload_bytes
    @test Base.summarysize(values) >= payload_bytes
    @test sizeof("α") == ncodeunits("α")
    # code_typed、sizeof 与 summarysize 都是锁定实现的观察入口，不是优化或对象布局保证。
end
