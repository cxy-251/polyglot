# polyglot-covers: julia.language.slice-copies-and-view-aliases

using Test

@testset "普通 slice 复制数据，view 与父数组共享存储" begin
    values = [10, 20, 30, 40]
    copied = values[2:3]
    borrowed = @view values[2:3]
    values[2] = 99
    @test copied == [20, 30]
    @test borrowed == [99, 30]
    borrowed[2] = 77
    @test values == [10, 99, 77, 40]
    @test parent(borrowed) === values
end
