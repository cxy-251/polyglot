# polyglot-covers: julia.runtime.buffered-channels-and-backpressure

using Test

@testset "有界 Channel 暴露容量、就绪和关闭状态" begin
    channel = Channel{Int}(1)
    @test !isready(channel)
    put!(channel, 7)
    @test isready(channel)
    @test take!(channel) == 7
    close(channel)
    @test !isopen(channel)
    @test_throws InvalidStateException put!(channel, 8)
end
