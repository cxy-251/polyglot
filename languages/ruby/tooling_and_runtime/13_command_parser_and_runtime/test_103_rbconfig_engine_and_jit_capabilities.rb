# frozen_string_literal: true
# polyglot-covers: ruby.tooling.rbconfig-engine-and-jit-capabilities

require "assertions"
require "rbconfig"

A = PolyglotAssertions

A.equal("ruby", RUBY_ENGINE)
A.equal("4.0.6", RUBY_VERSION)
A.truth(RbConfig.ruby.start_with?("/opt/polyglot/ruby-4.0.6/"))
A.equal("aarch64-linux", RbConfig::CONFIG.fetch("arch"))
A.includes(%w[linux linux-gnu], RbConfig::CONFIG.fetch("target_os"))
if RubyVM.const_defined?(:YJIT)
  A.falsey(RubyVM::YJIT.enabled?)
else
  A.truth(true)
end

if RubyVM.const_defined?(:ZJIT)
  A.falsey(RubyVM::ZJIT.enabled?)
else
  A.truth(true)
end

A.done
