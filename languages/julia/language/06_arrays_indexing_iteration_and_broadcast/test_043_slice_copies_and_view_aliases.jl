# polyglot-covers: julia.language.array-copy-view-mutation-and-aliasing

using Test

@testset "普通 slice 复制，view 和带感叹号操作保留别名" begin
    values = [10, 20, 30, 40]
    copied = values[2:3]
    borrowed = @view values[2:3]
    values[2] = 99
    @test copied == [20, 30]
    @test borrowed == [99, 30]
    borrowed[2] = 77
    @test values == [10, 99, 77, 40]
    @test parent(borrowed) === values
    alias = values
    sorted = sort(values)
    @test sorted == [10, 40, 77, 99]
    @test values == [10, 99, 77, 40]
    sort!(values)
    @test alias === values
    @test alias == sorted
    sizehint!(values, 16)
    @test values == sorted
end
