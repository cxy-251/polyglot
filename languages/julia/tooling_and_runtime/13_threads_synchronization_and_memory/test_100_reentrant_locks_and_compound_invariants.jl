# polyglot-covers: julia.runtime.reentrant-locks-and-invariants

using Test
using Base.Threads

@testset "ReentrantLock 保护复合 read-modify-write 不变量" begin
    guard = ReentrantLock()
    counter = Ref(0)
    tasks = [Threads.@spawn begin
        for _ in 1:100
            @lock guard counter[] += 1
        end
    end for _ in 1:8]
    fetch.(tasks)
    @test counter[] == 800
    @test !islocked(guard)
end
