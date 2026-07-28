# polyglot-family: async_and_concurrency
# polyglot-concept: async_await_and_result_propagation
# polyglot-related: languages/julia/tooling_and_runtime/12_tasks_channels_and_cooperative_concurrency/
# polyglot-related+: test_089_task_schedule_fetch_and_states.jl
#
# 共同问题：异步工作怎样返回结果和失败；等待是否等同于获取结果。
# 对照观察：Julia Task 由 schedule 启动，wait 等待完成，fetch 同时取得结果并传播 TaskFailedException。

using Test

@testset "Task 的完成状态和结果传播分离" begin
    success = schedule(@task 21 * 2)
    @test fetch(success) == 42
    @test istaskdone(success)
    failure = schedule(@task error("failed"))
    @test_throws TaskFailedException fetch(failure)
    @test istaskfailed(failure)
end
