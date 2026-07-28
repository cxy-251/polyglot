# polyglot-family: functions_and_calls
# polyglot-concept: scope_name_lookup_and_shadowing
# polyglot-related: languages/julia/language/03_scope_functions_closures_and_calls/
# polyglot-related+: test_018_lexical_scope_let_and_shadowing.jl
#
# 共同问题：词法作用域怎样查找名称；内层声明是修改外层 binding 还是建立遮蔽。
# 对照观察：函数和 let 是 hard scope；let 的新 binding 遮蔽外层，同一闭包可显式更新捕获 binding。

using Test

@testset "let 遮蔽不改写外层 binding" begin
    value = 1
    inside = let value = 2
        value + 1
    end
    @test inside == 3
    @test value == 1
    sandbox = Module()
    Core.eval(sandbox, :(function local_value(); hidden = 1; hidden end))
    @test !isdefined(sandbox, :hidden)
    @test Base.invokelatest(getfield(sandbox, :local_value)) == 1
end
