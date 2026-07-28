# polyglot-family: objects_and_dispatch
# polyglot-concept: introspection_reflection_and_runtime_type
# polyglot-related: languages/julia/tooling_and_runtime/15_reflection_time_and_runtime_observations/
# polyglot-related+: test_115_method_tables_applicable_and_hasmethod.jl
#
# 共同问题：运行时怎样查询类型、字段和可调用能力；反射结果哪些属于稳定接口。
# 对照观察：typeof/isa/fieldnames/methods 返回结构化语义；编译器文本和具体优化不作为跨版本契约。

using Test

@testset "结构化反射回答局部问题" begin
    value = (name = "Julia", version = v"1.12.6")
    @test typeof(value) <: NamedTuple
    @test value isa NamedTuple
    @test fieldnames(typeof(value)) == (:name, :version)
    @test hasmethod(getproperty, Tuple{typeof(value),Symbol})
    @test applicable(length, value)
end
