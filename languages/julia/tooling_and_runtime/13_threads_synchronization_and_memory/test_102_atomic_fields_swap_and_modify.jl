# polyglot-covers: julia.runtime.atomic-fields-swap-and-modify

using Test

mutable struct AtomicCounter
    @atomic value::Int
end

@testset "Julia 1.12 atomic field 宏声明并操作单个共享位置" begin
    counter = AtomicCounter(0)
    @atomic counter.value += 1
    @test (@atomic counter.value) == 1
    previous = @atomicswap counter.value = 5
    @test previous == 1
    @test (@atomic counter.value) == 5
    tasks = [Threads.@spawn begin
        for _ in 1:100
            @atomic counter.value += 1
        end
    end for _ in 1:4]
    fetch.(tasks)
    @test (@atomic counter.value) == 405
    # atomic 只覆盖一个位置；跨字段不变量仍需要 lock。
end
