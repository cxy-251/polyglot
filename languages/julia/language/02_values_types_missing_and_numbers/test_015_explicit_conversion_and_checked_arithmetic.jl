# polyglot-covers: julia.language.explicit-conversion-and-checked-arithmetic

using Test

@testset "显式转换区分可精确转换和信息丢失" begin
    @test Int(3.0) == 3
    @test_throws InexactError Int(3.5)
    @test UInt8(0xff) == 255
    @test_throws InexactError UInt8(256)
    @test_throws OverflowError Base.Checked.checked_add(typemax(Int), 1)
end
