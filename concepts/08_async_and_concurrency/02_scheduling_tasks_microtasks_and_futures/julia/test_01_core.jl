# polyglot-family: async_and_concurrency
# polyglot-concept: scheduling_tasks_microtasks_and_futures
# polyglot-related: languages/julia/tooling_and_runtime/12_tasks_channels_and_cooperative_concurrency/
# polyglot-related+: test_089_task_schedule_fetch_and_states.jl
#
# 共同问题：工作何时进入调度器；future/result handle 如何表示完成。
# 对照观察：Julia 没有 microtask 层；Task 是结果句柄，Channel 的 isready 只表示当前可消费状态。

using Test

@testset "schedule 返回同一 Task 句柄" begin
    task = @task begin
        yield()
        :done
    end
    @test !istaskstarted(task)
    @test schedule(task) === task
    @test fetch(task) === :done
    @test istaskdone(task)
    channel = Channel{Int}(1)
    @test !isready(channel)
    put!(channel, 7)
    @test isready(channel)
    @test take!(channel) == 7
    @test !isready(channel)
    close(channel)
end
