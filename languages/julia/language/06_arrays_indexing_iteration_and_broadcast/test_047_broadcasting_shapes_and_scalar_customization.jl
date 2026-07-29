# polyglot-covers: julia.language.broadcasting-shapes-and-scalar-customization

using Test

struct Offset
    value::Int
end

Base.broadcastable(offset::Offset) = Ref(offset)
Base.:+(value::Int, offset::Offset) = value + offset.value

@testset "broadcast 按轴扩展，custom scalar 通过 broadcastable 声明" begin
    values = [1, 2]
    row = [10 20]
    @test values .+ row == [11 21; 12 22]
    @test values .+ Offset(3) == [4, 5]
    @test_throws DimensionMismatch [1, 2, 3] .+ [10, 20]
    destination = zeros(Int, 2)
    destination .= values .* 4
    @test destination == [4, 8]
    @test Broadcast.combine_axes(values, row) == (Base.OneTo(2), Base.OneTo(2))
    flags = BitVector([true, false, true])
    flags .⊻= true
    @test flags == BitVector([false, true, false])
end
