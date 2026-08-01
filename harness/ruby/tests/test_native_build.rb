# frozen_string_literal: true

require "assertions"
require "polyglot_native"
require "rbconfig"

A = PolyglotAssertions

A.case("locked CRuby headers and shared-library suffix are available to extconf") do
  header_directory = RbConfig::CONFIG.fetch("rubyhdrdir")
  architecture_header = RbConfig::CONFIG.fetch("rubyarchhdrdir")

  A.equal("/opt/polyglot/ruby-4.0.6/include/ruby-4.0.0", header_directory)
  A.truth(File.file?(File.join(header_directory, "ruby.h")))
  A.truth(File.file?(File.join(header_directory, "ruby", "thread.h")))
  A.truth(File.file?(File.join(architecture_header, "ruby", "config.h")))
  A.equal("so", RbConfig::CONFIG.fetch("DLEXT"))
end

A.case("the repository extension builds and exposes its public Ruby API") do
  A.equal("CRuby 4.0.6", PolyglotNative::RELEASE)
  A.equal(42, PolyglotNative.add(20, 22))
end

A.done
