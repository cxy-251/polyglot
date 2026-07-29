# frozen_string_literal: true
# polyglot-covers: ruby.runtime.objectspace-dump-observation

require "assertions"
require "json"
require "objspace"

A = PolyglotAssertions

object = +"runtime"
document = JSON.parse(ObjectSpace.dump(object))

A.equal("STRING", document.fetch("type"))
A.equal(7, document.fetch("bytesize"))
A.truth(document.fetch("value").include?("runtime"))
A.truth(document.key?("address"))
A.equal("ruby", RUBY_ENGINE)

# address、shape 和 memsize 仅是锁定 CRuby 4.0.6 的诊断观察，不是 Ruby 语言保证。
A.truth(ObjectSpace.memsize_of(object).positive?)

A.done
