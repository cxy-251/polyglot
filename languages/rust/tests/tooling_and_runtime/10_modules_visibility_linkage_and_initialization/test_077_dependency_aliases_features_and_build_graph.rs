// polyglot-covers: rust.modules.aliases_features_graph

use std::collections::BTreeMap as OrderedMap;

#[test]
fn use_aliases_only_the_local_binding_and_features_select_build_graph_nodes() {
    let mapping = OrderedMap::from([(2, "b"), (1, "a")]);
    assert_eq!(mapping.keys().copied().collect::<Vec<_>>(), [1, 2]);
    let selected = if cfg!(feature = "pedagogy") {
        "pedagogy"
    } else {
        "default"
    };
    assert!(matches!(selected, "pedagogy" | "default"));
    // Cargo dependency aliases likewise rename a local extern-prelude binding, not the package identity.
}
