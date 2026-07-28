# polyglot-family: errors_and_resources
# polyglot-concept: exception_propagation_and_matching
# polyglot-related: languages/julia/language/07_unicode_exceptions_and_resources/
# polyglot-related+: test_056_custom_exceptions_and_diagnostic_rendering.jl
#
# 共同问题：异常怎样沿调用栈传播；处理器按什么规则匹配。
# 对照观察：Julia 使用单个 catch 并由 isa/dispatch 显式分类，未处理异常保持其结构化类型和值。

using Test

read_positive(value) = value > 0 ? value : throw(DomainError(value, "positive required"))

@testset "catch 中显式匹配异常类型" begin
    result = try
        read_positive(-1)
    catch exception
        exception isa DomainError ? exception.val : rethrow()
    end
    @test result == -1
    @test_throws DomainError read_positive(0)
end
