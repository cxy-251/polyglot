# polyglot-covers: julia.language.inner-outer-constructors-and-field-conversion

using Test

struct BoundedValue
    value::Int
    function BoundedValue(value::Int)
        0 <= value <= 100 || throw(ArgumentError("out of range"))
        return new(value)
    end
end

BoundedValue(value::AbstractFloat) = BoundedValue(round(Int, value))

struct Measurement
    count::Int
    ratio::Float64
end

@testset "inner constructor 守不变量，默认与 outer constructor 负责转换" begin
    @test BoundedValue(20).value == 20
    @test BoundedValue(19.6).value == 20
    @test_throws ArgumentError BoundedValue(101)
    measurement = Measurement(3.0, 2)
    @test measurement.count === 3
    @test measurement.ratio === 2.0
    @test fieldtypes(Measurement) == (Int, Float64)
    @test_throws InexactError Measurement(3.5, 2)
end
