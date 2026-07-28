# polyglot-covers: julia.language.parametric-methods-and-where-constraints

using Test

same_type(left::T, right::T) where {T} = T
same_type(left, right) = nothing
element_type(values::AbstractVector{T}) where {T<:Number} = T

@testset "where 参数连接多个实参类型并表达约束" begin
    @test same_type(1, 2) === Int
    @test same_type(1, 2.0) === nothing
    @test element_type(Int8[1, 2]) === Int8
    @test_throws MethodError element_type(["a"])
end
