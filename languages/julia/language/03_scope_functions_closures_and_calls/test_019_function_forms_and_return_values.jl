# polyglot-covers: julia.language.function-results-arguments-and-mutation

using Test

square(value) = value * value
rebind(values) = (values = [99])
mutate!(values) = push!(values, 3)

function classify(value)
    value < 0 && return :negative
    value == 0 && return :zero
    return :positive
end

@testset "返回值与参数 binding 的重新绑定、对象修改相互独立" begin
    @test square(4) == 16
    @test classify(-1) === :negative
    @test classify(0) === :zero
    @test classify(1) === :positive
    @test (value -> value + 1)(2) == 3
    values = [1, 2]
    @test rebind(values) == [99]
    @test values == [1, 2]
    @test mutate!(values) === values
    @test values == [1, 2, 3]
end
