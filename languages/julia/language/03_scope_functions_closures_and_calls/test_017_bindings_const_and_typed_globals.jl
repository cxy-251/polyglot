# polyglot-covers: julia.language.bindings-const-and-typed-globals

using Test

module BindingExamples
const immutable_binding = [1]
global typed_binding::Int = 2
end

@testset "const 固定 binding，typed global 转换赋值类型" begin
    push!(BindingExamples.immutable_binding, 2)
    @test BindingExamples.immutable_binding == [1, 2]
    BindingExamples.typed_binding = 3.0
    @test BindingExamples.typed_binding === 3
    @test_throws InexactError (BindingExamples.typed_binding = 3.5)
end
