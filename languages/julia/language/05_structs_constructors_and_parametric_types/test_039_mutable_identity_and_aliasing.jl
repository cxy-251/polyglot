# polyglot-covers: julia.language.mutable-identity-and-aliasing

using Test

mutable struct CounterBox
    value::Int
end

@testset "mutable 对象的身份区分相同字段值和同一别名" begin
    first = CounterBox(1)
    second = CounterBox(1)
    alias = first
    @test first !== second
    @test first === alias
    alias.value += 1
    @test first.value == 2
    @test second.value == 1
end
