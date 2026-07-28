# polyglot-covers: julia.language.argument-binding-and-mutation

using Test

rebind(values) = (values = [99])
mutate!(values) = push!(values, 3)

@testset "参数 binding 按共享值传递，重新绑定和对象修改不同" begin
    values = [1, 2]
    replacement = rebind(values)
    @test values == [1, 2]
    @test replacement == [99]
    @test mutate!(values) === values
    @test values == [1, 2, 3]
end
