# polyglot-covers: julia.tooling.macro-hygiene-and-escape

using Test

macro twice(expression)
    return quote
        local captured = $(esc(expression))
        captured + captured
    end
end

macro assign(binding, value)
    return :($(esc(binding)) = $(esc(value)))
end

@testset "macro local 自动 hygiene，esc 将调用方表达式放回调用作用域" begin
    captured = 5
    @test @twice(captured + 1) == 12
    @assign assigned 9
    @test assigned == 9
    @test captured == 5
end
