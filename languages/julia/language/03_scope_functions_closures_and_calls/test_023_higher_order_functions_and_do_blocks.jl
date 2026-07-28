# polyglot-covers: julia.language.higher-order-functions-and-do-blocks

using Test

with_value(action, value) = action(value)

@testset "do block 把匿名函数作为第一个参数传递" begin
    result = with_value(5) do value
        value * 2
    end
    @test result == 10
    @test map(x -> x^2, 1:4) == [1, 4, 9, 16]
    @test filter(iseven, 1:6) == [2, 4, 6]
end
