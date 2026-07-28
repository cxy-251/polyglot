# polyglot-covers: julia.stdlib.set-membership-and-algebra

using Test

@testset "Set 去重并按成员关系表达集合代数" begin
    left = Set([1, 2, 2, 3])
    right = Set([3, 4])
    @test left == Set([1, 2, 3])
    @test union(left, right) == Set([1, 2, 3, 4])
    @test intersect(left, right) == Set([3])
    @test setdiff(left, right) == Set([1, 2])
    @test issubset(Set([1, 2]), left)
end
