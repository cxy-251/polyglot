# polyglot-covers: julia.stdlib.sha-digests-and-hex-encoding

using Test
using SHA

@testset "SHA 返回固定长度摘要，hex 只改变展示编码" begin
    digest = sha256("abc")
    @test length(digest) == 32
    @test bytes2hex(digest) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    @test sha1("abc") != sha1("abd")
    @test hex2bytes(bytes2hex(digest)) == digest
end
