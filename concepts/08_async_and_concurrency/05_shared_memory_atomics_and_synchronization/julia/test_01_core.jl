# polyglot-family: async_and_concurrency
# polyglot-concept: shared_memory_atomics_and_synchronization
# polyglot-related: languages/julia/tooling_and_runtime/13_threads_synchronization_and_memory/
# polyglot-related+: test_102_atomic_fields_swap_and_modify.jl
#
# 共同问题：共享单位置更新怎样原子化；复合不变量何时需要 lock。
# 对照观察：Julia 1.12 @atomic 保护声明的 field 操作，ReentrantLock 保护跨多个步骤的临界区。

using Test

mutable struct AtomicCounter
    @atomic value::Int
end

@testset "atomic field 和 lock 覆盖不同粒度" begin
    counter = AtomicCounter(0)
    @test (@atomic counter.value += 1) == 1
    @test (@atomic :acquire counter.value) == 1
    lock = ReentrantLock()
    values = Int[]
    @lock lock push!(values, counter.value)
    @test values == [1]
end
