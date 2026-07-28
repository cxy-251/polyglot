# polyglot-covers: julia.stdlib.ranges-steps-and-lazy-indexing

using Test

@testset "Range 紧凑表示规则序列并支持索引而不物化数组" begin
    integers = 2:3:11
    @test collect(integers) == [2, 5, 8, 11]
    @test integers[3] == 8
    @test length(integers) == 4
    points = range(0.0, 1.0; length = 5)
    @test collect(points) == [0.0, 0.25, 0.5, 0.75, 1.0]
    @test step(integers) == 3
end
