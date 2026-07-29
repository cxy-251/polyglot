# polyglot-covers: julia.language.bindings-lexical-scope-and-typed-globals

using Test

module BindingExamples
const immutable_binding = [1]
global typed_binding::Int = 2

function scoped_values()
    outer = 1
    inner = let outer = outer + 1
        outer * 10
    end
    return outer, inner
end
end

@testset "binding、const、typed global 与 lexical shadowing 分层" begin
    push!(BindingExamples.immutable_binding, 2)
    @test BindingExamples.immutable_binding == [1, 2]
    BindingExamples.typed_binding = 3.0
    @test BindingExamples.typed_binding === 3
    @test_throws InexactError (BindingExamples.typed_binding = 3.5)
    @test BindingExamples.scoped_values() == (1, 20)
    @test !isdefined(Main, :outer)
end
