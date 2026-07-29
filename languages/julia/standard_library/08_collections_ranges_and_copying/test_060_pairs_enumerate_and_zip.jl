# polyglot-covers: julia.stdlib.iteration-adapters-ranges-and-zip

using Test

@testset "pairs、enumerate、zip 和 range 保持各自的惰性结构" begin
    values = ["a", "b"]
    @test collect(pairs(values)) == [1 => "a", 2 => "b"]
    @test collect(enumerate(values)) == [(1, "a"), (2, "b")]
    @test collect(zip(values, 10:11)) == [("a", 10), ("b", 11)]
    @test collect(zip(1:3, [:a])) == [(1, :a)]
    integers = 2:3:11
    @test collect(integers) == [2, 5, 8, 11]
    @test integers[3] == 8
    @test step(integers) == 3
    points = range(0.0, 1.0; length = 5)
    @test collect(points) == [0.0, 0.25, 0.5, 0.75, 1.0]
end
