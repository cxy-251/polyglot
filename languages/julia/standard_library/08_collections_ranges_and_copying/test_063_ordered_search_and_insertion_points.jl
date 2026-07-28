# polyglot-covers: julia.stdlib.ordered-search-and-insertion-points

using Test

@testset "searchsorted 系列在已排序输入上返回区间或插入点" begin
    values = [1, 3, 3, 5]
    @test searchsorted(values, 3) == 2:3
    @test searchsortedfirst(values, 4) == 4
    @test searchsortedlast(values, 0) == 0
    @test insorted(5, values)
    @test !insorted(2, values)
end
