# polyglot-family: collections_and_iteration
# polyglot-concept: iteration_protocol
# polyglot-related: languages/julia/language/06_arrays_indexing_iteration_and_broadcast/
# polyglot-related+: test_045_custom_iteration_protocol.jl
#
# 共同问题：iterable 与 iterator 是否必须分离；一次性消费如何显式表达。
# 对照观察：普通 Julia iterable 可重复调用 iterate；Iterators.Stateful 把外部状态包装成可继续消费对象。

using Test

@testset "Stateful 显式保存消费位置" begin
    stateful = Iterators.Stateful(1:3)
    @test popfirst!(stateful) == 1
    @test collect(stateful) == [2, 3]
    @test isempty(stateful)
    @test collect(1:3) == collect(1:3)
end
