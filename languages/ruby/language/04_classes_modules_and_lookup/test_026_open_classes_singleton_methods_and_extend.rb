# frozen_string_literal: true
# polyglot-covers: ruby.objects.singleton-class-methods-and-extend

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

class OpenClassFixture
  def original
    :original
  end
end

instance_created_before_reopen = OpenClassFixture.new
class OpenClassFixture
  def added_later
    :added
  end
end

A.case("reopening a class changes the existing class object and earlier instances") do
  A.equal(:added, instance_created_before_reopen.added_later)
end

feature = Module.new do
  def feature
    :extended
  end
end
object = Object.new
def object.only_here = :singleton
object.extend(feature)

A.case("singleton methods and extend alter only one object's singleton-class lookup") do
  other = Object.new
  A.equal([:singleton, :extended], [object.only_here, object.feature])
  A.falsey(other.respond_to?(:only_here))
  A.falsey(other.respond_to?(:feature))
  A.includes(object.singleton_class.ancestors, feature)
  A.same(object.singleton_class, class << object; self; end)
end

A.case("an open-class patch is process-local rather than a persistent runtime change") do
  code = <<~'RUBY'
    class String
      def polyglot_marker = :child
    end
    print "ruby".polyglot_marker
  RUBY
  stdout, stderr, status = H.ruby_command("-e", code)

  A.truth(status.success?, stderr)
  A.equal("child", stdout)
  A.falsey("ruby".respond_to?(:polyglot_marker))
end

A.done
