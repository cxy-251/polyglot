# polyglot-covers: julia.runtime.channel-buffering-producers-iteration-and-close

using Test

@testset "Channel 容量表达 backpressure，producer 完成后关闭迭代" begin
    channel = Channel{Int}(1)
    @test !isready(channel)
    put!(channel, 7)
    @test isready(channel)
    @test take!(channel) == 7
    close(channel)
    @test !isopen(channel)
    @test_throws InvalidStateException put!(channel, 8)
    produced = Channel{Int}(0) do output
        for value in 1:3
            put!(output, value^2)
        end
    end
    @test collect(produced) == [1, 4, 9]
    @test !isopen(produced)
end
