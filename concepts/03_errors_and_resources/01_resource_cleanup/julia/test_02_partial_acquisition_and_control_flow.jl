# polyglot-family: errors_and_resources
# polyglot-concept: resource_cleanup
# polyglot-related: languages/julia/language/07_unicode_exceptions_and_resources/
# polyglot-related+: test_054_try_catch_finally_and_rethrow.jl
#
# 共同问题：部分资源取得后失败怎样回滚；return 是否跳过 cleanup。
# 对照观察：finally 在 return 和 throw 前执行；只清理已经成功取得且由当前作用域拥有的资源。

using Test

function controlled_exit(log, fail)
    acquired = false
    try
        push!(log, :acquire)
        acquired = true
        fail && error("after acquire")
        return :done
    finally
        acquired && push!(log, :release)
    end
end

@testset "finally 保持 acquisition/release 配对" begin
    normal = Symbol[]
    @test controlled_exit(normal, false) == :done
    @test normal == [:acquire, :release]
    failing = Symbol[]
    @test_throws ErrorException controlled_exit(failing, true)
    @test failing == [:acquire, :release]
end
