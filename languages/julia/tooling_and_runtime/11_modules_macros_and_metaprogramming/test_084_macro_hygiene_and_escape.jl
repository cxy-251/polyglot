# polyglot-covers: julia.tooling.expr-quotation-macro-hygiene-and-escape

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
    binding = :x
    expression = :($binding + $(2 * 3))
    @test expression.head === :call
    @test expression.args == [:+, :x, 6]
    target = Module(:ExpressionTarget)
    Core.eval(target, :(const x = 1))
    @test Core.eval(target, expression) == 7
    captured = 5
    @test @twice(captured + 1) == 12
    @assign assigned 9
    @test assigned == 9
    @test captured == 5
    expanded = macroexpand(@__MODULE__, :(@twice captured))
    @test expanded isa Expr
end
