# polyglot-covers: julia.language.missing-propagation-and-coalescing

using Test

@testset "missing 表示统计未知并按运算协议传播" begin
    @test ismissing(missing)
    @test 1 + missing === missing
    @test ismissing(missing == missing)
    @test isequal(missing, missing)
    @test coalesce(missing, 9) == 9
    @test collect(skipmissing([1, missing, 3])) == [1, 3]
end
