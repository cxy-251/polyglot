# polyglot-family: time_locale_and_runtime
# polyglot-concept: runtime_capabilities_versions_and_feature_detection
# polyglot-related: languages/julia/tooling_and_runtime/15_reflection_time_and_runtime_observations/
# polyglot-related+: test_116_lowered_and_typed_code_as_scoped_observations.jl
#
# 共同问题：稳定语义接口与实现观察怎样分层；编译器输出能否写成永久保证。
# 对照观察：结构化 reflection 可检查调用形状；lowered/typed IR 只锁定本课程的 1.12.6 局部观察，不比较文本。

using Test

increment(value::Int) = value + 1

@testset "只对 compiler reflection 断言结构和当前版本范围" begin
    @test increment(1) == 2
    lowered = code_lowered(increment, Tuple{Int})
    @test length(lowered) == 1
    @test lowered[1] isa Core.CodeInfo
    @test VERSION == v"1.12.6"
    @test which(increment, (Int,)).module === @__MODULE__
end
