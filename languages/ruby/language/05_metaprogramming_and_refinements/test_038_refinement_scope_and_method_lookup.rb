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

A.case("outside the activating lexical scope the target keeps its ordinary lookup") do
  target = RefinementTarget.new
  A.equal(:base, target.label)
  A.falsey(target.respond_to?(:refined_only))
  A.falsey(RefinementTarget.instance_methods(false).include?(:refined_only))
end

A.case("using activates refined methods lexically and super continues ordinary lookup") do
  target = RefinementTarget.new
  A.equal([[:refined, :base], :available], RefinementLexicalScope.read(target))
  A.equal(:base, target.label)
end

A.case("using accepts a refinement module rather than an arbitrary class") do
  A.raises(TypeError) { Module.new.module_eval { using Class.new } }
end

A.done
