# polyglot-covers: julia.language.iteration-protocol-generators-and-termination

using Test

struct Countdown
    start::Int
end

function Base.iterate(sequence::Countdown, state = sequence.start)
    state < 0 && return nothing
    return state, state - 1
end

Base.IteratorSize(::Type{Countdown}) = Base.SizeUnknown()
Base.eltype(::Type{Countdown}) = Int

@testset "iterate 驱动 pull protocol，generator 只按消费求值" begin
    @test collect(Countdown(3)) == [3, 2, 1, 0]
    @test iterate(Countdown(1)) == (1, 0)
    @test iterate(Countdown(1), -1) === nothing
    @test eltype(Countdown) === Int
    pulls = Ref(0)
    generator = ((pulls[] += 1; value^2) for value in 1:10)
    @test pulls[] == 0
    @test collect(Iterators.take(generator, 2)) == [1, 4]
    @test pulls[] == 2
    @test collect(Iterators.filter(iseven, 1:6)) == [2, 4, 6]
end
