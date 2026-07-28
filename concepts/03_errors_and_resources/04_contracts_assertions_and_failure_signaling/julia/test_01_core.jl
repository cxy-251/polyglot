# polyglot-family: errors_and_resources
# polyglot-concept: contracts_assertions_and_failure_signaling
# polyglot-related: languages/julia/tooling_and_runtime/01_toolchain_project_and_testing/
# polyglot-related+: test_002_testsets_assertions_and_failures.jl
#
# 共同问题：程序员不变量、输入错误和测试失败如何选择不同信号。
# 对照观察：@assert 抛 AssertionError；公共输入边界通常显式抛 ArgumentError/DomainError。

using Test

positive(value) = value > 0 ? value : throw(DomainError(value))

@testset "失败类型表达契约层次" begin
    @test_throws AssertionError @assert 1 == 2
    @test_throws DomainError positive(0)
    @test_throws ArgumentError only(Int[])
    @test positive(2) == 2
end
