# polyglot-family: collections_and_iteration
# polyglot-concept: generators_laziness_and_early_termination
# polyglot-related: languages/julia/language/06_arrays_indexing_iteration_and_broadcast/
# polyglot-related+: test_046_generators_laziness_and_early_termination.jl
#
# 共同问题：generator 何时求值；消费者提前停止时后续元素是否执行。
# 对照观察：Julia generator 按 iterate 请求求值；Iterators.take 限制请求数量，不需要先物化源序列。

using Test

@testset "消费数量控制 generator 副作用" begin
    seen = Int[]
    generator = (begin
        push!(seen, value)
        value^2
    end for value in 1:5)
    @test isempty(seen)
    @test collect(Iterators.take(generator, 2)) == [1, 4]
    @test seen == [1, 2]
end
