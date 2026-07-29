# polyglot-covers: julia.stdlib.subprocess-io-status-environment-and-cwd

using Test

function isolated_julia(expression)
    return `$(Base.julia_cmd()) --startup-file=no --history-file=no --project=@stdlib
        --depwarn=error --check-bounds=yes --threads=1 --color=no -e $expression`
end

@testset "Cmd 显式承载 IO、状态、环境和工作目录边界" begin
    @test read(isolated_julia("print(6 * 7)"), String) == "42"
    transformed = pipeline(isolated_julia("print(\"julia\")"), `tr a-z A-Z`)
    @test read(transformed, String) == "JULIA"
    failed = isolated_julia("exit(3)")
    process = run(ignorestatus(failed))
    @test process.exitcode == 3
    @test !success(process)
    parent_value = get(ENV, "POLYGLOT_CHILD_VALUE", nothing)
    command = addenv(
        isolated_julia("print(ENV[\"POLYGLOT_CHILD_VALUE\"])"),
        "POLYGLOT_CHILD_VALUE" => "child",
    )
    @test read(command, String) == "child"
    @test get(ENV, "POLYGLOT_CHILD_VALUE", nothing) === parent_value
    mktempdir(prefix = "polyglot-julia-") do directory
        cwd_command = Cmd(isolated_julia("print(pwd())"); dir = directory)
        @test read(cwd_command, String) == directory
        @test pwd() != directory
    end
end
