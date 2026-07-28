# polyglot-covers: julia.language.array-mutation-and-alias-boundaries

using Test

@testset "带感叹号操作修改原数组，非感叹号操作返回新数组" begin
    values = [3, 1, 2]
    alias = values
    sorted = sort(values)
    @test sorted == [1, 2, 3]
    @test values == [3, 1, 2]
    sort!(values)
    @test alias === values
    @test alias == [1, 2, 3]
    sizehint!(values, 16)
    @test values == [1, 2, 3]
end
