# polyglot-family: async_and_concurrency
# polyglot-concept: shared_memory_atomics_and_synchronization
# polyglot-related: languages/julia/tooling_and_runtime/13_threads_synchronization_and_memory/
# polyglot-related+: test_101_condition_variables_and_predicate_loops.jl
#
# 共同问题：read-modify-write 怎样避免丢更新；通知能否代替状态 predicate。
# 对照观察：lock 覆盖完整复合更新；Threads.Condition 与同一 lock 配合，waiter 总在循环中检查状态。

using Test
using Base.Threads

@testset "临界区和 predicate 共同定义同步协议" begin
    mutex = ReentrantLock()
    count = Ref(0)
    @sync for _ in 1:20
        Threads.@spawn @lock mutex count[] += 1
    end
    @test count[] == 20
    condition = Threads.Condition()
    ready = Ref(false)
    waiter = Threads.@spawn lock(condition) do
        while !ready[]
            wait(condition)
        end
        :ready
    end
    lock(condition) do
        ready[] = true
        notify(condition)
    end
    @test fetch(waiter) === :ready
end
