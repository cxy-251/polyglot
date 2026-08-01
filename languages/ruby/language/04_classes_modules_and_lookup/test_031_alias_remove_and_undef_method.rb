# frozen_string_literal: true
# polyglot-covers: ruby.objects.alias-remove-and-undef-method

require "assertions"

A = PolyglotAssertions

base = Class.new do
  def value
    :base
  end
end

aliasing = Class.new(base) do
  alias_method :original_value, :value

  def value
    :child
  end
end

removing = Class.new(aliasing) do
  def value
    :temporary
  end

  remove_method :value
end

undefining = Class.new(base) do
  undef_method :value
end

A.case("alias_method captures the method entry visible when the alias is created") do
  A.equal(:child, aliasing.new.value)
  A.equal(:base, aliasing.new.original_value)
end

A.case("remove_method removes the local entry and reveals an ancestor implementation") do
  A.equal(:child, removing.new.value)
end

A.case("undef_method installs a lookup barrier instead of revealing the ancestor") do
  A.raises(NoMethodError) { undefining.new.value }
  A.falsey(undefining.method_defined?(:value))
end

A.done
