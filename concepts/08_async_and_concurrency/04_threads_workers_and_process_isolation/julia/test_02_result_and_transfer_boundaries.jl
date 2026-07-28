# polyglot-family: async_and_concurrency
# polyglot-concept: threads_workers_and_process_isolation
# polyglot-related: languages/julia/tooling_and_runtime/13_threads_synchronization_and_memory/
# polyglot-related+: test_103_channel_publication_across_threads.jl
#
# 共同问题：并发结果是共享引用还是传输副本；同步边界是否建立可见性。
# 对照观察：同进程 Channel 传递对象引用并同步发布；进程间需显式编码，不能保留对象身份。

using Test
using Base.Threads

@testset "Channel 发布共享对象而文本传输只保留值" begin
    source = [1, 2]
    channel = Channel{Vector{Int}}(1)
    producer = Threads.@spawn put!(channel, source)
    received = take!(channel)
    wait(producer)
    @test received === source
    encoded = repr(source)
    @test encoded == "[1, 2]"
    @test encoded !== source
end
