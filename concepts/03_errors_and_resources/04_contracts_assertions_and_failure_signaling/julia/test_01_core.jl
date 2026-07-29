# polyglot-family: errors_and_resources
# polyglot-concept: contracts_assertions_and_failure_signaling
# polyglot-related: languages/julia/language/07_unicode_exceptions_and_resources/
# polyglot-related+: test_054_try_catch_finally_and_rethrow.jl
#
# 共同问题：程序员不变量、输入错误和测试失败如何选择不同信号。
# 对照观察：@assert、异常、nothing 和 MethodError 表达不同失败层次，通道由 API 契约决定。

using Test

positive(value) = value > 0 ? value : throw(DomainError(value))
accept_integer(value::Int) = value

@testset "失败类型表达契约层次" begin
    @test_throws AssertionError @assert 1 == 2
    @test_throws DomainError positive(0)
    @test_throws ArgumentError only(Int[])
    @test positive(2) == 2
    @test tryparse(Int, "bad") === nothing
    @test_throws ArgumentError parse(Int, "bad")
    @test accept_integer(2) == 2
    @test_throws MethodError accept_integer(2.0)
end
