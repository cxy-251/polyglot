# polyglot-family: functions_and_calls
# polyglot-concept: closures_capture_and_lifetime
# polyglot-related: languages/julia/language/03_scope_functions_closures_and_calls/
# polyglot-related+: test_024_closure_capture_and_fresh_bindings.jl
#
# 共同问题：闭包捕获值还是 binding；创建函数返回后状态能否继续存在。
# 对照观察：Julia 闭包共享词法 binding；工厂的每次调用创建独立环境，let 可固定循环值。

using Test

function counter()
    value = 0
    return () -> (value += 1)
end

@testset "闭包拥有独立且持久的词法状态" begin
    first = counter()
    second = counter()
    @test (first(), first(), second()) == (1, 2, 1)
    callbacks = [let captured = item; () -> captured end for item in 1:3]
    @test map(callback -> callback(), callbacks) == [1, 2, 3]
end
