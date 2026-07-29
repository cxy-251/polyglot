# polyglot-covers: julia.language.higher-order-functions-do-blocks-and-closures

using Test

with_value(action, value) = action(value)

function counters()
    shared = 0
    increment = () -> (shared += 1)
    read = () -> shared
    return increment, read
end

@testset "do block 传递函数，closure 捕获 binding 而不是值快照" begin
    result = with_value(5) do value
        value * 2
    end
    @test result == 10
    @test map(x -> x^2, 1:4) == [1, 4, 9, 16]
    @test filter(iseven, 1:6) == [2, 4, 6]
    increment, read = counters()
    @test (increment(), increment(), read()) == (1, 2, 2)
    callbacks = [let captured = value; () -> captured; end for value in 1:3]
    @test map(callback -> callback(), callbacks) == [1, 2, 3]
end
