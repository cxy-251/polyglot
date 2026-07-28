# polyglot-covers: julia.language.keyword-and-optional-arguments

using Test

scale(value, offset = 0; factor = 1, clamp = nothing) = begin
    result = (value + offset) * factor
    clamp === nothing ? result : min(result, clamp)
end

@testset "可选位置参数生成调用形状，keyword 按名称绑定" begin
    @test scale(3) == 3
    @test scale(3, 2; factor = 4) == 20
    @test scale(3; clamp = 2) == 2
    options = (; factor = 3, clamp = 10)
    @test scale(2; options...) == 6
end
