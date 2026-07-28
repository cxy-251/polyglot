# polyglot-covers: julia.tooling.generated-functions-and-type-inputs

using Test

@generated function storage_category(::Type{T}) where {T}
    return isbitstype(T) ? QuoteNode(:bits) : QuoteNode(:reference)
end

@testset "generated function 生成阶段只能依赖参数类型和早先定义" begin
    @test storage_category(Int) === :bits
    @test storage_category(Float64) === :bits
    @test storage_category(Vector{Int}) === :reference
    @test storage_category(String) === :reference
end
