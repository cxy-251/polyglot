# polyglot-covers: julia.language.numeric-models-and-overflow

using Test

@testset "数值类型保留各自的表示与算术边界" begin
    @test Int8(127) + Int8(1) == typemin(Int8)
    @test 1 // 3 + 1 // 6 == 1 // 2
    @test (1 + 2im) * (1 - 2im) == 5 + 0im
    @test 0.1 + 0.2 != 0.3
    @test isapprox(0.1 + 0.2, 0.3)
    @test big"2"^200 > typemax(Int128)
end
