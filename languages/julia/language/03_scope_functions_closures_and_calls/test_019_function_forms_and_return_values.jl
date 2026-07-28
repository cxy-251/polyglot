# polyglot-covers: julia.language.function-forms-and-return-values

using Test

square(value) = value * value

function classify(value)
    value < 0 && return :negative
    value == 0 && return :zero
    return :positive
end

@testset "函数体最后一个表达式和显式 return 都能产生结果" begin
    @test square(4) == 16
    @test classify(-1) === :negative
    @test classify(0) === :zero
    @test classify(1) === :positive
    @test (value -> value + 1)(2) == 3
end
