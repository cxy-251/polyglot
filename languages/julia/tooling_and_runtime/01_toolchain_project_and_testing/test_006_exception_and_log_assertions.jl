# polyglot-covers: julia.toolchain.exception-and-log-assertions

using Test
using Logging

function validate_port(port)
    1 <= port <= 65_535 || throw(DomainError(port, "port out of range"))
    return port
end

@testset "异常类型与日志是独立可断言的观察面" begin
    @test validate_port(8080) == 8080
    @test_throws DomainError validate_port(0)
    @test_logs (:warn, "fallback") @warn "fallback"
end
