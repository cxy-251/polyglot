# frozen_string_literal: true
# polyglot-covers: ruby.runtime.rubygems-and-bundler-environment-isolation

require "assertions"
require "pathname"
require "rubygems"

A = PolyglotAssertions

home = Pathname.new(ENV.fetch("HOME"))
gem_home = Pathname.new(ENV.fetch("GEM_HOME"))
bundle_home = Pathname.new(ENV.fetch("BUNDLE_USER_HOME"))
A.truth(home.to_s.include?("/tmp/polyglot-ruby-"))
A.truth(gem_home.to_s.start_with?(home.parent.to_s))
A.truth(bundle_home.to_s.start_with?(home.parent.to_s))
A.equal(gem_home.to_s, Gem.dir)
A.includes(Gem.path, gem_home.to_s)
A.equal("/dev/null", ENV.fetch("GEMRC"))
A.equal("true", ENV.fetch("BUNDLE_ALLOW_OFFLINE_INSTALL"))

A.done
