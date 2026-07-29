# polyglot-family: async_and_concurrency
# polyglot-concept: cancellation_timeouts_and_cleanup
# polyglot-related: languages/julia/tooling_and_runtime/12_tasks_channels_and_cooperative_concurrency/
# polyglot-related+: test_096_timers_and_predicate_timeouts.jl
#
# 共同问题：timeout 是否自动取消底层工作；超时后谁仍拥有并收尾任务。
# 对照观察：timedwait 只等待 predicate 并返回状态，不取消 Task；调用方仍须唤醒、等待或转移所有权。

using Test

@testset "timeout 不隐式取消被等待任务" begin
    event = Base.Event()
    task = @async begin
        wait(event)
        :finished
    end
    @test timedwait(() -> istaskdone(task), 0.01) === :timed_out
    @test !istaskdone(task)
    notify(event)
    @test fetch(task) === :finished
end
