# frozen_string_literal: true
# polyglot-covers: ruby.metaprogramming.refinement-lexical-activation

require "assertions"

A = PolyglotAssertions

class RefinementTarget
  def label
    :base
  end
end

module LabelRefinement
  refine RefinementTarget do
    def label
      [:refined, super]
    end

    def refined_only
      :available
    end
  end
end

module RefinementLexicalScope
  using LabelRefinement

  def self.read(target)
    [target.label, target.refined_only]
  end
end

target = RefinementTarget.new
A.equal(:base, target.label)
A.falsey(target.respond_to?(:refined_only))
A.equal([[:refined, :base], :available], RefinementLexicalScope.read(target))
# using 是词法激活，不修改目标类，也不会泄漏到调用者作用域。
A.equal(:base, target.label)
A.falsey(RefinementTarget.instance_methods(false).include?(:refined_only))
A.raises(TypeError) { Module.new.module_eval { using Class.new } }

A.done
