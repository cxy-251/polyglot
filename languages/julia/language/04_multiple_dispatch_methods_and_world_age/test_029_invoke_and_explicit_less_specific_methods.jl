# polyglot-covers: julia.language.invoke-less-specific-method

using Test

describe(value::Number) = "number:$value"
describe(value::Int) = "int:$value"

@testset "invoke 可显式调用指定签名的较不具体方法" begin
    @test describe(3) == "int:3"
    @test invoke(describe, Tuple{Number}, 3) == "number:3"
    @test which(describe, (Int,)).sig <: Tuple{typeof(describe),Int}
end
