# polyglot-covers: julia.runtime.channel-bound-producers-and-iteration

using Test

@testset "Channel do constructor 绑定 producer task 并在返回后关闭" begin
    channel = Channel{Int}(0) do output
        for value in 1:3
            put!(output, value^2)
        end
    end
    @test collect(channel) == [1, 4, 9]
    @test !isopen(channel)
end
