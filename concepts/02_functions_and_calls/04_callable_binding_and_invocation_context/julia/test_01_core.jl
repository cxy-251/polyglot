# polyglot-family: functions_and_calls
# polyglot-concept: callable_binding_and_invocation_context
# polyglot-related: languages/julia/language/04_multiple_dispatch_methods_and_world_age/
# polyglot-related+: test_030_callable_objects_and_dispatch.jl
#
# 共同问题：可调用值怎样携带状态；调用上下文是否隐式绑定接收者。
# 对照观察：Julia 函数和 callable struct 都通过 method dispatch 调用，没有类方法的隐式 this/self。

using Test

struct ScaleBy
    factor::Int
end

(scale::ScaleBy)(value::Int) = scale.factor * value

@testset "可调用对象的状态是显式字段" begin
    double = ScaleBy(2)
    @test double(5) == 10
    @test applicable(double, 5)
    @test !applicable(double, "5")
    @test which(double, (Int,)).sig <: Tuple
end
