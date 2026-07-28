# polyglot-covers: julia.tooling.expr-quote-and-interpolation

using Test

@testset "Expr 表示语法树，quote interpolation 插入语法或已求值数据" begin
    binding = :x
    expression = :($binding + $(2 * 3))
    @test expression.head === :call
    @test expression.args == [:+, :x, 6]
    target = Module(:ExpressionTarget)
    Core.eval(target, :(const x = 1))
    @test Core.eval(target, expression) == 7
    @test Meta.show_sexpr(IOBuffer(), expression) === nothing
end
