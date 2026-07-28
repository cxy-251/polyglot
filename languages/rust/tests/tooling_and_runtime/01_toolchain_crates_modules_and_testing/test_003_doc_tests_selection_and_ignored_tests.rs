// polyglot-covers: rust.tooling.doc_tests_selection_ignored

#[test]
fn test_names_are_filterable_stable_identifiers() {
    assert!(module_path!().ends_with("course_003"));
    assert_eq!(polyglot_rust_course::checked_double(4), Some(8));
}

#[test]
#[ignore = "教学用 ignored test：默认基线验证忽略项，显式使用 --ignored 才运行"]
fn ignored_tests_require_explicit_selection() {
    assert_eq!(2 + 2, 4);
}
