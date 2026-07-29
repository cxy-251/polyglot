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
      :refined
    end
  end
end

module RefinementLexicalScope
  using LabelRefinement

  def self.read(target)
    target.label
  end
end

target = RefinementTarget.new
A.equal(:base, target.label)
A.equal(:refined, RefinementLexicalScope.read(target))
A.equal(:base, target.label)
A.falsey(RefinementTarget.instance_methods(false).include?(:refined_label))

A.done
