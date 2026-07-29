# frozen_string_literal: true
# polyglot-covers: ruby.objects.method-visibility

require "assertions"

A = PolyglotAssertions

visibility_class = Class.new do
  def public_value
    private_value
  end

  def compare(other)
    other.protected_value
  end

  protected

  def protected_value
    :protected
  end

  private

  def private_value
    :private
  end
end

object = visibility_class.new
A.equal(:private, object.public_value)
A.equal(:protected, object.compare(visibility_class.new))
A.raises(NoMethodError) { object.private_value }
A.raises(NoMethodError) { object.protected_value }
A.truth(visibility_class.private_instance_methods(false).include?(:private_value))
A.truth(visibility_class.protected_instance_methods(false).include?(:protected_value))

A.done
