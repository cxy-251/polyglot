# polyglot-covers: julia.language.closure-capture-and-fresh-bindings

using Test

function counters()
    shared = 0
    increment = () -> (shared += 1)
    read = () -> shared
    return increment, read
end

@testset "闭包共享外层 binding，let 可为循环创建新 binding" begin
    increment, read = counters()
    @test increment() == 1
    @test increment() == 2
    @test read() == 2
    callbacks = [let captured = value; () -> captured; end for value in 1:3]
    @test map(callback -> callback(), callbacks) == [1, 2, 3]
end
