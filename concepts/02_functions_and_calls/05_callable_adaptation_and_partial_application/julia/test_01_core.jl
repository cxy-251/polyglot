# polyglot-family: functions_and_calls
# polyglot-concept: callable_adaptation_and_partial_application
# polyglot-related: languages/julia/language/03_scope_functions_closures_and_calls/
# polyglot-related+: test_023_higher_order_functions_and_do_blocks.jl
#
# 共同问题：怎样固定部分参数、适配调用形状并保持原函数语义。
# 对照观察：Julia 用 closure、Fix1/Fix2 和 do block 显式适配；适配器仍参加普通 dispatch。

using Test

@testset "部分应用不复制函数实现" begin
    starts_with_pre = Base.Fix1(startswith, "prefix")
    @test starts_with_pre("pre")
    @test !starts_with_pre("suffix")
    subtract_from_ten = Base.Fix1(-, 10)
    @test subtract_from_ten(3) == 7
    @test map(Base.Fix2(^, 2), 1:3) == [1, 4, 9]
end
