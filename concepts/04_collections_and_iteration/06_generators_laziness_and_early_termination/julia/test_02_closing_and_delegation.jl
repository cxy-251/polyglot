# polyglot-family: collections_and_iteration
# polyglot-concept: generators_laziness_and_early_termination
# polyglot-related: languages/julia/tooling_and_runtime/12_tasks_channels_and_cooperative_concurrency/
# polyglot-related+: test_092_channel_bound_producers_and_iteration.jl
#
# 共同问题：生产者如何声明完成；提前终止是否有通用 close/delegation 协议。
# 对照观察：Julia generator 没有统一 close/yield-from 协议；Channel 用 close 和迭代显式表达生产完成。

using Test

@testset "Channel 的关闭状态终止迭代" begin
    channel = Channel{Int}(2) do output
        put!(output, 1)
        put!(output, 2)
    end
    @test collect(channel) == [1, 2]
    @test !isopen(channel)
    @test_throws InvalidStateException put!(channel, 3)
end
