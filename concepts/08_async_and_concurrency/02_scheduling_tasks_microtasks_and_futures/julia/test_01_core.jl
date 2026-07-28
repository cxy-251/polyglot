# polyglot-family: async_and_concurrency
# polyglot-concept: scheduling_tasks_microtasks_and_futures
# polyglot-related: languages/julia/tooling_and_runtime/12_tasks_channels_and_cooperative_concurrency/
# polyglot-related+: test_089_task_schedule_fetch_and_states.jl
#
# 共同问题：工作何时进入调度器；future/result handle 如何表示完成。
# 对照观察：Julia 没有 JavaScript microtask 层；schedule 把 Task 交给 cooperative scheduler，Task 本身是结果句柄。

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
end
