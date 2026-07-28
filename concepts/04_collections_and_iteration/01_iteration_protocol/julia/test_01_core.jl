# polyglot-family: collections_and_iteration
# polyglot-concept: iteration_protocol
# polyglot-related: languages/julia/language/06_arrays_indexing_iteration_and_broadcast/
# polyglot-related+: test_045_custom_iteration_protocol.jl
#
# 共同问题：可迭代值怎样产生元素和终止；状态由对象还是调用者持有。
# 对照观察：Julia iterate(iterable[, state]) 返回 (value, next_state) 或 nothing，状态显式在线程外传递。

using Test

struct Countdown
    start::Int
end

Base.iterate(counter::Countdown, state = counter.start) = state < 1 ? nothing : (state, state - 1)
Base.IteratorSize(::Type{Countdown}) = Base.SizeUnknown()

@testset "iterate 的结束哨兵与元素值分离" begin
    @test iterate(Countdown(2)) == (2, 1)
    @test iterate(Countdown(2), 0) === nothing
    @test collect(Countdown(3)) == [3, 2, 1]
end
