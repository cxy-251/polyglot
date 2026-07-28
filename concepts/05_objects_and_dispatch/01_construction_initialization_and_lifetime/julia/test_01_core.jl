# polyglot-family: objects_and_dispatch
# polyglot-concept: construction_initialization_and_lifetime
# polyglot-related: languages/julia/language/05_structs_constructors_and_parametric_types/
# polyglot-related+: test_034_inner_and_outer_constructors.jl
#
# 共同问题：构造过程怎样维护不变量；对象是否有隐式析构生命周期。
# 对照观察：inner constructor 决定实例是否可创建，outer constructor 适配输入；GC 对象没有确定析构时点。

using Test

struct PositiveCount
    value::Int
    PositiveCount(value::Int) = value > 0 ? new(value) : throw(ArgumentError("positive"))
end

PositiveCount(text::AbstractString) = PositiveCount(parse(Int, text))

@testset "inner constructor 守住所有构造入口" begin
    @test PositiveCount(2).value == 2
    @test PositiveCount("3").value == 3
    @test_throws ArgumentError PositiveCount(0)
end
