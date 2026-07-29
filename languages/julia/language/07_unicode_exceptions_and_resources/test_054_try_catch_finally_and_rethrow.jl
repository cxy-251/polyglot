# polyglot-covers: julia.language.exceptions-rethrow-finally-and-diagnostics

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

struct ValidationError <: Exception
    field::Symbol
    reason::String
end

function Base.showerror(io::IO, error::ValidationError)
    print(io, "invalid ", error.field, ": ", error.reason)
end

@testset "异常类型承载数据，catch/rethrow 与 finally 控制传播" begin
    events = Symbol[]
    @test controlled_failure(events) === :handled
    @test events == [:try, :catch, :finally]
    error = ValidationError(:port, "out of range")
    @test error.field === :port
    @test sprint(showerror, error) == "invalid port: out of range"
    @test_throws ValidationError throw(error)
end
