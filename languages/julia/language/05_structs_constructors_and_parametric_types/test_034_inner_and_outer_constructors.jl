# polyglot-covers: julia.language.inner-and-outer-constructors

using Test

struct BoundedValue
    value::Int
    function BoundedValue(value::Int)
        0 <= value <= 100 || throw(ArgumentError("out of range"))
        return new(value)
    end
end

BoundedValue(value::AbstractFloat) = BoundedValue(round(Int, value))

@testset "inner constructor 守住不变量，outer constructor 负责适配输入" begin
    @test BoundedValue(20).value == 20
    @test BoundedValue(19.6).value == 20
    @test_throws ArgumentError BoundedValue(101)
end
