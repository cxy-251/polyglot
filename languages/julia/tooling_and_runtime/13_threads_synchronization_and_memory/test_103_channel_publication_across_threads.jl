# polyglot-covers: julia.runtime.channel-publication-across-threads

using Test
using Base.Threads

@testset "Channel 在线程间发布拥有的值并建立同步边界" begin
    channel = Channel{Vector{Int}}(1)
    producer = Threads.@spawn begin
        value = [1, 2]
        push!(value, 3)
        put!(channel, value)
        return :published
    end
    received = take!(channel)
    @test received == [1, 2, 3]
    @test fetch(producer) === :published
    close(channel)
end
