# polyglot-family: objects_and_dispatch
# polyglot-concept: encapsulation_private_state_and_immutability
# polyglot-related: languages/julia/language/05_structs_constructors_and_parametric_types/
# polyglot-related+: test_033_immutable_and_mutable_structs.jl
#
# 共同问题：私有状态和不可变性由语言还是约定保证；不可变对象能否包含可变成员。
# 对照观察：struct 字段 binding 不可改且模块命名提供封装约定；字段无 class-private 权限，可变成员仍能修改。

using Test

struct ImmutableEnvelope
    items::Vector{Int}
end

@testset "immutable 固定字段 binding 而非递归冻结对象图" begin
    envelope = ImmutableEnvelope([1])
    push!(envelope.items, 2)
    @test envelope.items == [1, 2]
    @test_throws ErrorException setfield!(envelope, :items, Int[])
    @test fieldnames(ImmutableEnvelope) == (:items,)
end
