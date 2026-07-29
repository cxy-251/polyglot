# polyglot-covers: julia.language.numeric-models-conversion-and-promotion

using Test

@testset "数值表示、转换和 promotion 明确区分" begin
    @test Int8(127) + Int8(1) == typemin(Int8)
    @test_throws OverflowError Base.Checked.checked_add(typemax(Int), 1)
    @test 1 // 3 + 1 // 6 == 1 // 2
    @test (1 + 2im) * (1 - 2im) == 5 + 0im
    @test 0.1 + 0.2 != 0.3
    @test isapprox(0.1 + 0.2, 0.3)
    @test big"2"^200 > typemax(Int128)
    @test Int(3.0) == 3
    @test_throws InexactError Int(3.5)
    @test_throws InexactError UInt8(256)
    @test promote(1, 2.5) === (1.0, 2.5)
    @test promote_type(Int, Float64) === Float64
    @test !(Int <: Float64)
    @test 1 + 2.5 == 3.5
end
