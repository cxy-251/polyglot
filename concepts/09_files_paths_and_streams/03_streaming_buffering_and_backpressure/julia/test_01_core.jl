# polyglot-family: files_paths_and_streams
# polyglot-concept: streaming_buffering_and_backpressure
# polyglot-related: languages/julia/tooling_and_runtime/12_tasks_channels_and_cooperative_concurrency/
# polyglot-related+: test_091_buffered_channels_and_backpressure_state.jl
#
# 共同问题：buffer 怎样分离生产和消费；容量满时如何表达 backpressure。
# 对照观察：IOBuffer 管理字节 cursor；有界 Channel 以 put!/take! 同步生产者，不靠 sleep 推断流量。

using Test

@testset "有界缓冲区暴露可消费状态" begin
    bytes = IOBuffer()
    write(bytes, "chunk")
    seekstart(bytes)
    @test read(bytes, String) == "chunk"
    channel = Channel{String}(1)
    put!(channel, "first")
    @test isready(channel)
    @test take!(channel) == "first"
    @test !isready(channel)
end
