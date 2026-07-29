# frozen_string_literal: true
# polyglot-covers: ruby.objects.singleton-class-methods-and-extend

require "assertions"

A = PolyglotAssertions

feature = Module.new do
  def feature
    :extended
  end
end

object = Object.new
def object.only_here
  :singleton
end
object.extend(feature)

other = Object.new
A.equal(:singleton, object.only_here)
A.equal(:extended, object.feature)
A.falsey(other.respond_to?(:only_here))
A.falsey(other.respond_to?(:feature))
A.same(object.singleton_class, class << object; self; end)
A.includes(object.singleton_class.ancestors, feature)
A.same(Class, object.singleton_class.class)

A.done
