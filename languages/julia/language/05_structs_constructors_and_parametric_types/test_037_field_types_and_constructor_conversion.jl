# polyglot-covers: julia.language.field-types-and-constructor-conversion

using Test

struct Measurement
    count::Int
    ratio::Float64
end

@testset "默认 constructor 对有声明类型的字段执行 convert" begin
    measurement = Measurement(3.0, 2)
    @test measurement.count === 3
    @test measurement.ratio === 2.0
    @test fieldtypes(Measurement) == (Int, Float64)
    @test_throws InexactError Measurement(3.5, 2)
end
