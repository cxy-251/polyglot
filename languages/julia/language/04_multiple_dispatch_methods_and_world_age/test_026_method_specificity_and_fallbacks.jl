# polyglot-covers: julia.language.method-specificity-and-fallbacks

using Test

category(value::Number) = :number
category(value::Integer) = :integer
category(value::Int) = :machine_integer
category(value) = :other

@testset "更具体的适用方法优先于抽象 fallback" begin
    @test category(1) === :machine_integer
    @test category(big"1") === :integer
    @test category(1.5) === :number
    @test category("1") === :other
end
