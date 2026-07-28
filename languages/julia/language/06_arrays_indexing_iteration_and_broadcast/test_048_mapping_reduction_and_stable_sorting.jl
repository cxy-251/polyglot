# polyglot-covers: julia.language.mapping-reduction-and-stable-sorting

using Test

@testset "collection pipeline 显式选择映射、归约和稳定排序" begin
    @test map(abs, [-2, 1]) == [2, 1]
    @test mapreduce(x -> x^2, +, 1:4) == 30
    @test findall(iseven, 1:6) == [2, 4, 6]
    records = [(1, :first), (2, :middle), (1, :last)]
    sorted = sort(records; by = first, alg = Base.Sort.MergeSort)
    @test sorted == [(1, :first), (1, :last), (2, :middle)]
    @test partialsort([5, 1, 4, 2], 2) == 2
end
