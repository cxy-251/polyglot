# polyglot-covers: julia.language.varargs-optional-and-keyword-arguments

using Test

summarize(head, tail...) = (head, length(tail), sum(tail))
scale(value, offset = 0; factor = 1, clamp = nothing) = begin
    result = (value + offset) * factor
    clamp === nothing ? result : min(result, clamp)
end

@testset "位置、varargs、splat 与 keyword 使用不同绑定规则" begin
    values = (1, 2, 3, 4)
    @test summarize(values...) == (1, 3, 9)
    first, second, rest... = values
    @test (first, second, rest) == (1, 2, (3, 4))
    @test [0; values...] == [0, 1, 2, 3, 4]
    @test scale(3, 2; factor = 4) == 20
    options = (; factor = 3, clamp = 10)
    @test scale(2; options...) == 6
    @test_throws MethodError scale(2; unknown = true)
end
