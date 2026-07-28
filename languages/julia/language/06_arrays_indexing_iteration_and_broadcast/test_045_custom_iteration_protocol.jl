# polyglot-covers: julia.language.custom-iteration-protocol

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

@testset "iterate 返回 value/state 或 nothing 结束序列" begin
    @test collect(Countdown(3)) == [3, 2, 1, 0]
    @test iterate(Countdown(1)) == (1, 0)
    @test iterate(Countdown(1), -1) === nothing
    @test eltype(Countdown) === Int
end
