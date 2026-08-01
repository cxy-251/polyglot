# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.digest-secure-random-and-prng

require "assertions"
require "digest"
require "securerandom"

A = PolyglotAssertions

A.case("digest functions deterministically map bytes to algorithm-sized hex output") do
  A.equal(
    "098f6bcd4621d373cade4e832627b4f6",
    Digest::MD5.hexdigest("test")
  )
  A.equal(64, Digest::SHA256.hexdigest("ruby").length)
end

A.case("seeded Random is reproducible while SecureRandom only promises output shape here") do
  first = Random.new(1234)
  second = Random.new(1234)
  A.equal(5.times.map { first.rand(1000) }, 5.times.map { second.rand(1000) })
  A.truth(SecureRandom.hex(8).match?(/\A[0-9a-f]{16}\z/))
  A.equal(16, SecureRandom.random_bytes(16).bytesize)
end

A.done
