# polyglot-family: async_and_concurrency
# polyglot-concept: scheduling_tasks_microtasks_and_futures
# polyglot-related: languages/julia/tooling_and_runtime/12_tasks_channels_and_cooperative_concurrency/
# polyglot-related+: test_094_events_and_explicit_wakeup.jl
#
# 共同问题：ready 表示任务已完成还是资源可消费；测试能否依赖队列内部顺序。
# 对照观察：isready(Channel) 只观察当前可 take 状态；代码通过 Channel/Event 同步，不锁定 scheduler 队列顺序。

using Test

@testset "就绪状态通过同步对象观察" begin
    channel = Channel{Int}(1)
    @test !isready(channel)
    put!(channel, 7)
    @test isready(channel)
    @test take!(channel) == 7
    @test !isready(channel)
    close(channel)
end
