# polyglot-family: errors_and_resources
# polyglot-concept: contracts_assertions_and_failure_signaling
# polyglot-related: languages/julia/language/07_unicode_exceptions_and_resources/
# polyglot-related+: test_052_parsing_and_tryparse_failure_values.jl
#
# 共同问题：可预期失败何时返回值、何时抛异常；类型边界何时拒绝调用。
# 对照观察：tryparse 返回 nothing，parse 抛异常；multiple dispatch 对无适用签名抛 MethodError。

using Test

accept_integer(value::Int) = value

@testset "失败通道由 API 契约决定" begin
    @test tryparse(Int, "bad") === nothing
    @test_throws ArgumentError parse(Int, "bad")
    @test accept_integer(2) == 2
    @test_throws MethodError accept_integer(2.0)
end
