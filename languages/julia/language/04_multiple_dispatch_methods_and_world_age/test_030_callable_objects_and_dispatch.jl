# polyglot-covers: julia.language.callable-objects-and-dispatch

using Test

struct Affine{T}
    scale::T
    offset::T
end

(transform::Affine)(value::Number) = transform.scale * value + transform.offset

@testset "对象可通过其类型的方法参与调用分派" begin
    transform = Affine(2, 3)
    @test transform(4) == 11
    @test transform(1.5) == 6.0
    @test applicable(transform, 1)
    @test !applicable(transform, "1")
end
