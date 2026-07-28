# polyglot-covers: julia.language.try-catch-finally-and-rethrow

using Test

function controlled_failure(events)
    try
        push!(events, :try)
        throw(ArgumentError("invalid"))
    catch error
        push!(events, :catch)
        error isa ArgumentError || rethrow()
        return :handled
    finally
        push!(events, :finally)
    end
end

@testset "catch 选择处理路径，finally 在返回前执行" begin
    events = Symbol[]
    @test controlled_failure(events) === :handled
    @test events == [:try, :catch, :finally]
end
