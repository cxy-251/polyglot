# frozen_string_literal: true
# polyglot-covers: ruby.runtime.locked-runtime-contract

require "assertions"
require "polyglot_native"

A = PolyglotAssertions

A.equal("ruby", RUBY_ENGINE)
A.equal("4.0.6", RUBY_VERSION)
A.equal("03b6d3f8898a28604fe6cb00eae3226b821168f4", RUBY_REVISION)
A.matches(/\Aruby 4\.0\.6 .* \+PRISM \[aarch64-linux\]\z/, RUBY_DESCRIPTION)
A.equal("CRuby 4.0.6", PolyglotNative::RELEASE)

A.truth(Object.new.is_a?(Object))
A.truth(proc {}.is_a?(Proc))
A.truth(Thread.new { 42 }.value == 42)
A.truth(Ractor::Port.new.is_a?(Ractor::Port))

A.done
