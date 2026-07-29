# polyglot-covers: julia.language.method-ambiguity-and-disambiguation

using Test

ambiguous(left::Int, right) = :left
ambiguous(left, right::Int) = :right

resolved(left::Int, right) = :left
resolved(left, right::Int) = :right
resolved(left::Int, right::Int) = :both

@testset "互不更具体的方法会产生歧义，交集方法显式解除歧义" begin
    @test_throws MethodError ambiguous(1, 2)
    @test ambiguous(1, "x") === :left
    @test ambiguous("x", 1) === :right
    @test resolved(1, 2) === :both
    @test !Base.isambiguous(
        which(resolved, (Int, Int)),
        which(resolved, (Int, Any)),
    )
    @test !isempty(detect_ambiguities(@__MODULE__; recursive = false))
end
