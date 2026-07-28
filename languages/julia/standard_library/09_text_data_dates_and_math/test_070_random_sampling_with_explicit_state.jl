# polyglot-covers: julia.stdlib.random-explicit-state-and-sampling

using Test
using Random

@testset "Random API 可将状态作为显式对象传递" begin
    first_rng = MersenneTwister(42)
    second_rng = MersenneTwister(42)
    @test rand(first_rng, 1:10, 5) == rand(second_rng, 1:10, 5)
    values = collect(1:8)
    shuffled = shuffle(MersenneTwister(7), values)
    @test sort(shuffled) == values
    @test shuffled != values
end
