# polyglot-covers: julia.runtime.condition-variables-and-predicates

using Test
using Base.Threads

@testset "Threads.Condition 与同一 lock 配合并循环检查 predicate" begin
    guard = ReentrantLock()
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
