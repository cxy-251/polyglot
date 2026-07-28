# polyglot-covers: julia.stdlib.bit-arrays-and-bit-sets

using Test

@testset "BitArray 压缩布尔值，BitSet 面向非负整数成员" begin
    flags = BitVector([true, false, true])
    @test flags isa BitVector
    @test count(flags) == 2
    flags .⊻= true
    @test flags == BitVector([false, true, false])
    values = BitSet([1, 3, 3])
    @test collect(values) == [1, 3]
    @test 3 in values
end
