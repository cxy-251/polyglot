# polyglot-covers: julia.language.custom-exceptions-and-diagnostics

using Test

struct ValidationError <: Exception
    field::Symbol
    reason::String
end

function Base.showerror(io::IO, error::ValidationError)
    print(io, "invalid ", error.field, ": ", error.reason)
end

@testset "异常类型携带结构化数据，showerror 只负责诊断文本" begin
    error = ValidationError(:port, "out of range")
    @test error.field === :port
    @test sprint(showerror, error) == "invalid port: out of range"
    @test_throws ValidationError throw(error)
end
