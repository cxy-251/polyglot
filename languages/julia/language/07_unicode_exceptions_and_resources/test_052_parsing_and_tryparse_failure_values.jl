# polyglot-covers: julia.language.parsing-and-tryparse

using Test

@testset "parse 抛出失败，tryparse 用 nothing 表示无法解析" begin
    @test parse(Int, "42") == 42
    @test parse(Float64, "1.5") == 1.5
    @test tryparse(Int, "invalid") === nothing
    @test_throws ArgumentError parse(Int, "invalid")
    @test parse(Bool, "true") === true
end
