# polyglot-family: async_and_concurrency
# polyglot-concept: cancellation_timeouts_and_cleanup
# polyglot-related: languages/julia/tooling_and_runtime/12_tasks_channels_and_cooperative_concurrency/
# polyglot-related+: test_095_cooperative_cancellation_protocol.jl
#
# 共同问题：取消由谁发起和确认；cleanup 是否在协作停止路径执行。
# 对照观察：Julia Task 没有通用强制 cancel；应用通过 Channel/Event 传递停止协议并用 finally 清理。

using Test

@testset "协作停止拥有明确确认与 cleanup" begin
    stop = Channel{Nothing}(1)
    cleaned = Ref(false)
    task = @async try
        take!(stop)
        :stopped
    finally
        cleaned[] = true
    end
    put!(stop, nothing)
    @test fetch(task) === :stopped
    @test cleaned[]
end
