# frozen_string_literal: true

require "assertions"
require "rbconfig"

A = PolyglotAssertions

A.equal("ruby", RUBY_ENGINE)
A.equal("4.0.6", RUBY_VERSION)
A.equal("03b6d3f8898a28604fe6cb00eae3226b821168f4", RUBY_REVISION)
A.matches(/\Aruby 4\.0\.6 .* \+PRISM \[aarch64-linux\]\z/, RUBY_DESCRIPTION)
A.equal("/opt/polyglot/ruby-4.0.6/bin/ruby", RbConfig.ruby)
A.equal("aarch64-linux", RbConfig::CONFIG.fetch("arch"))

A.done
