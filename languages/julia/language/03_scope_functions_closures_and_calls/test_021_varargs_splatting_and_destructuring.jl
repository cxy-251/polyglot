# polyglot-covers: julia.language.varargs-splatting-and-destructuring

using Test

summarize(head, tail...) = (head, length(tail), sum(tail))

@testset "varargs 收集位置参数，splat 在调用点展开" begin
    values = (1, 2, 3, 4)
    @test summarize(values...) == (1, 3, 9)
    first, second, rest... = values
    @test (first, second, rest) == (1, 2, (3, 4))
    @test [0; values...] == [0, 1, 2, 3, 4]
end
