# polyglot-family: errors_and_resources
# polyglot-concept: error_chaining_suppression_and_aggregation
# polyglot-related: languages/julia/language/07_unicode_exceptions_and_resources/
# polyglot-related+: test_054_try_catch_finally_and_rethrow.jl
#
# 共同问题：处理异常时产生的新异常是否保留上下文；上下文能否被结构化检查。
# 对照观察：Julia 的 current_exceptions 记录当前 task 的 exception stack，没有跨语言统一的 cause 字段。

using Test

function nested_exception_stack()
    try
        error("root")
    catch
        try
            throw(ArgumentError("wrapper"))
        catch
            return current_exceptions()
        end
    end
end

@testset "exception stack 保留同一 task 的嵌套失败" begin
    stack = nested_exception_stack()
    @test length(stack) == 2
    @test stack[1].exception isa ErrorException
    @test stack[2].exception isa ArgumentError
end
