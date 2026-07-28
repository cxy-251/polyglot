# polyglot-covers: julia.runtime.cconvert-unsafe-convert-and-gc-preserve

using Test

@testset "cconvert 产生保活对象，unsafe_convert 取得临时 ABI pointer" begin
    converted = Base.cconvert(Cstring, "hello")
    pointer = Base.unsafe_convert(Cstring, converted)
    GC.@preserve converted begin
        @test unsafe_string(pointer) == "hello"
        @test unsafe_load(Ptr{UInt8}(pointer)) == UInt8('h')
    end
end
