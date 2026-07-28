# polyglot-family: objects_and_dispatch
# polyglot-concept: inheritance_dynamic_dispatch_and_super
# polyglot-related: languages/julia/language/04_multiple_dispatch_methods_and_world_age/
# polyglot-related+: test_029_invoke_and_explicit_less_specific_methods.jl
#
# 共同问题：实现复用与运行时分派怎样组织；如何显式调用较一般实现。
# 对照观察：Julia concrete type 不继承字段实现；abstract type 组织开放方法，invoke 选择较不具体签名。

using Test

abstract type Pet end
struct Cat <: Pet end

speak(::Pet) = "pet"
speak(::Cat) = "cat+" * invoke(speak, Tuple{Pet}, Cat())

@testset "抽象层次参与 multiple dispatch" begin
    @test Cat <: Pet
    @test speak(Cat()) == "cat+pet"
    @test which(speak, (Cat,)).sig == Tuple{typeof(speak),Cat}
    @test_throws MethodError Pet()
end
