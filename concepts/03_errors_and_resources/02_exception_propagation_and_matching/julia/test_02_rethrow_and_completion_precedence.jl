# polyglot-family: errors_and_resources
# polyglot-concept: exception_propagation_and_matching
# polyglot-related: languages/julia/language/07_unicode_exceptions_and_resources/
# polyglot-related+: test_054_try_catch_finally_and_rethrow.jl
#
# 共同问题：rethrow 是否保留原异常；cleanup 自身失败时哪个 completion 离开作用域。
# 对照观察：rethrow() 传播当前异常；finally 的新 throw 会成为外层直接观察到的异常。

using Test

function completion_precedence()
    try
        throw(ArgumentError("body"))
    finally
        throw(ErrorException("cleanup"))
    end
end

@testset "finally 的异常成为直接传播结果" begin
    exception = try
        completion_precedence()
    catch caught
        caught
    end
    @test exception isa ErrorException
    @test exception.msg == "cleanup"
end
