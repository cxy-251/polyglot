# polyglot-covers: julia.language.generators-laziness-and-early-termination

using Test

@testset "generator 按消费拉取并可由 take 提前终止" begin
    pulls = Ref(0)
    generator = ((pulls[] += 1; value^2) for value in 1:10)
    @test pulls[] == 0
    @test collect(Iterators.take(generator, 2)) == [1, 4]
    @test pulls[] == 2
    @test collect(Iterators.filter(iseven, 1:6)) == [2, 4, 6]
end
