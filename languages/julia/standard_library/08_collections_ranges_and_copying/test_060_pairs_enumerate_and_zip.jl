# polyglot-covers: julia.stdlib.pairs-enumerate-and-zip

using Test

@testset "pairs、enumerate 和 zip 暴露不同的键与位置关系" begin
    values = ["a", "b"]
    @test collect(pairs(values)) == [1 => "a", 2 => "b"]
    @test collect(enumerate(values)) == [(1, "a"), (2, "b")]
    @test collect(zip(values, 10:11)) == [("a", 10), ("b", 11)]
    @test collect(zip(1:3, [:a])) == [(1, :a)]
end
