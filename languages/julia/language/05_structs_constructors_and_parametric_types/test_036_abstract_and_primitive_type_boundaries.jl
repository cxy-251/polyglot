# polyglot-covers: julia.language.abstract-and-primitive-type-boundaries

using Test

abstract type CourseNumber <: Number end
primitive type Token64 <: CourseNumber 64 end

@testset "abstract type 不可实例化，primitive type 声明位宽和层次" begin
    @test !isconcretetype(CourseNumber)
    @test isconcretetype(Token64)
    @test sizeof(Token64) == 8
    @test Token64 <: CourseNumber <: Number
    @test_throws MethodError CourseNumber()
end
