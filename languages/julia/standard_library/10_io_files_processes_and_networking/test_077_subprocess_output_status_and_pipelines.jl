# polyglot-covers: julia.stdlib.subprocess-output-status-and-pipelines

using Test

function isolated_julia(expression)
    return `$(Base.julia_cmd()) --startup-file=no --history-file=no --project=@stdlib
        --depwarn=error --check-bounds=yes --threads=1 --color=no -e $expression`
end

@testset "Cmd、read 和 pipeline 分离输出、状态与数据流" begin
    @test read(isolated_julia("print(6 * 7)"), String) == "42"
    transformed = pipeline(isolated_julia("print(\"julia\")"), `tr a-z A-Z`)
    @test read(transformed, String) == "JULIA"
    failed = isolated_julia("exit(3)")
    process = run(ignorestatus(failed))
    @test process.exitcode == 3
    @test !success(process)
end
