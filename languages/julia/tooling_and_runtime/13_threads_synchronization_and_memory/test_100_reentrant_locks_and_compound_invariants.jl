# polyglot-covers: julia.runtime.locks-condition-predicates-and-invariants

using Test
using Base.Threads

@testset "同一 lock 同时保护复合更新与 Condition predicate" begin
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
    condition = Threads.Condition(guard)
    ready = Ref(false)
    waiter = Threads.@spawn begin
        lock(guard)
        try
            while !ready[]
                wait(condition)
            end
            return :ready
        finally
            unlock(guard)
        end
    end
    lock(guard)
    try
        ready[] = true
        notify(condition)
    finally
        unlock(guard)
    end
    @test fetch(waiter) === :ready
end
