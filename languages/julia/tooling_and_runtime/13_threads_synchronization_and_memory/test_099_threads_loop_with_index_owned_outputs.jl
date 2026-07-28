# polyglot-covers: julia.runtime.threads-loop-index-owned-output

using Test
using Base.Threads

@testset "@threads 迭代各写独占索引，不依赖任务分块和执行顺序" begin
    output = zeros(Int, 32)
    Threads.@threads for index in eachindex(output)
        output[index] = index^2
    end
    @test output == [index^2 for index in eachindex(output)]
    @test sum(output) == sum(index^2 for index in 1:32)
end
