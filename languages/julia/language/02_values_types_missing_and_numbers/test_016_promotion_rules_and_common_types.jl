# polyglot-covers: julia.language.promotion-rules-and-common-types

using Test

@testset "promotion 选择共同表示而不是建立子类型关系" begin
    promoted = promote(1, 2.5)
    @test promoted === (1.0, 2.5)
    @test promote_type(Int8, UInt8) === UInt8
    @test promote_type(Int, Float64) === Float64
    @test !(Int <: Float64)
    @test 1 + 2.5 == 3.5
end
