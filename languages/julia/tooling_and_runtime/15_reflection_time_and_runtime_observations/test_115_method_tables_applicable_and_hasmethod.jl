# polyglot-covers: julia.runtime.method-tables-and-applicability

using Test

runtime_method(value::Int) = value + 1
runtime_method(value::AbstractString) = uppercase(value)

@testset "methods、which、applicable 和 hasmethod 查询不同层次" begin
    @test length(methods(runtime_method)) == 2
    @test which(runtime_method, (Int,)).name === :runtime_method
    @test applicable(runtime_method, 1)
    @test !applicable(runtime_method, 1.0)
    @test hasmethod(runtime_method, Tuple{AbstractString})
end
