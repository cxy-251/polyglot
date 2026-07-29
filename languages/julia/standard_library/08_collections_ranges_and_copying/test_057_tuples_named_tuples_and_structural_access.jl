# polyglot-covers: julia.stdlib.tuples-and-named-tuples

using Test

@testset "Tuple 固定位置结构，NamedTuple 增加编译期字段名" begin
    tuple_value = (1, "two")
    named = (count = 1, label = "two")
    @test tuple_value[2] == "two"
    @test named.label == "two"
    @test keys(named) == (:count, :label)
    @test merge(named, (count = 3,)) == (count = 3, label = "two")
    @test NamedTuple{(:x, :y)}((1, 2)) == (x = 1, y = 2)
    @test typeof(named) === NamedTuple{(:count, :label),Tuple{Int,String}}
    @test_throws BoundsError tuple_value[3]
    @test_throws MethodError setindex!(tuple_value, 3, 1)
end
