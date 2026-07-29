# polyglot-family: async_and_concurrency
# polyglot-concept: async_await_and_result_propagation
# polyglot-related: languages/julia/tooling_and_runtime/12_tasks_channels_and_cooperative_concurrency/
# polyglot-related+: test_089_task_schedule_fetch_and_states.jl
#
# 共同问题：父作用域是否拥有子任务；多个子任务失败如何被完整收集。
# 对照观察：@sync 等待词法范围内的 @async，并把失败作为 CompositeException 传播给拥有者。

using Test

@testset "@sync 建立结构化任务所有权" begin
    completed = Channel{Symbol}(2)
    @sync begin
        @async put!(completed, :first)
        @async put!(completed, :second)
    end
    @test Set([take!(completed), take!(completed)]) == Set([:first, :second])
    @test_throws CompositeException @sync @async error("owned failure")
end
