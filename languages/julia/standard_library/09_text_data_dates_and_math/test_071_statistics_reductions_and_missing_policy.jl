# polyglot-covers: julia.stdlib.statistics-reductions-and-missing-policy

using Test
using Statistics

@testset "Statistics reduction 的缺失值策略由调用方显式选择" begin
    values = [1.0, 2.0, 3.0, 4.0]
    @test mean(values) == 2.5
    @test median(values) == 2.5
    @test std(values; corrected = false) ≈ sqrt(1.25)
    with_missing = Union{Missing,Float64}[1.0, missing, 3.0]
    @test mean(skipmissing(with_missing)) == 2.0
    @test ismissing(mean(with_missing))
    @test isnan(mean(Float64[]))
    @test_throws ArgumentError median(Float64[])
end
