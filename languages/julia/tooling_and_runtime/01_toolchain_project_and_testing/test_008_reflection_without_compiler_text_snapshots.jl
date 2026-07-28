# polyglot-covers: julia.toolchain.structured-reflection-not-text-snapshots

using Test
using InteractiveUtils

increment(value::Int) = value + 1

@testset "结构化反射优先于编译器文本快照" begin
    expression = Meta.parse("x + 1")
    @test expression.head == :call
    @test expression.args[1] == :+
    @test which(increment, (Int,)).name == :increment
    @test !isempty(code_lowered(increment, (Int,)))
end
