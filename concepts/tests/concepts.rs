mod concept_01_01_01 {
    include!(concat!(
        "../01_values_and_comparison/01_truthiness/rust/",
        "test_01_core.rs"
    ));
}
mod concept_01_02_01 {
    include!(concat!(
        "../01_values_and_comparison/02_equality/rust/",
        "test_01_core.rs"
    ));
}
mod concept_01_03_01 {
    include!(concat!(
        "../01_values_and_comparison/03_numeric_models_and_conversion/rust/",
        "test_01_core.rs"
    ));
}
mod concept_01_04_01 {
    include!(concat!(
        "../01_values_and_comparison/04_null_missing_and_optional_values/rust/",
        "test_01_core.rs"
    ));
}
mod concept_01_05_01 {
    include!(concat!(
        "../01_values_and_comparison/05_identity_aliasing_and_copying/rust/",
        "test_01_core.rs"
    ));
}
mod concept_01_06_01 {
    include!(concat!(
        "../01_values_and_comparison/06_ordering_hashing_and_key_semantics/rust/",
        "test_01_core.rs"
    ));
}
mod concept_02_01_01 {
    include!(concat!(
        "../02_functions_and_calls/01_argument_passing/rust/",
        "test_01_core.rs"
    ));
}
mod concept_02_02_01 {
    include!(concat!(
        "../02_functions_and_calls/02_scope_name_lookup_and_shadowing/rust/",
        "test_01_core.rs"
    ));
}
mod concept_02_03_01 {
    include!(concat!(
        "../02_functions_and_calls/03_closures_capture_and_lifetime/rust/",
        "test_01_core.rs"
    ));
}
mod concept_02_04_01 {
    include!(concat!(
        "../02_functions_and_calls/04_callable_binding_and_invocation_context/rust/",
        "test_01_core.rs"
    ));
}
mod concept_02_05_01 {
    include!(concat!(
        "../02_functions_and_calls/05_callable_adaptation_and_partial_application/rust/",
        "test_01_core.rs"
    ));
}
mod concept_03_01_01 {
    include!(concat!(
        "../03_errors_and_resources/01_resource_cleanup/rust/",
        "test_01_core.rs"
    ));
}
mod concept_03_01_02 {
    include!(concat!(
        "../03_errors_and_resources/01_resource_cleanup/rust/",
        "test_02_partial_acquisition_and_control_flow.rs"
    ));
}
mod concept_03_02_01 {
    include!(concat!(
        "../03_errors_and_resources/02_exception_propagation_and_matching/rust/",
        "test_01_core.rs"
    ));
}
mod concept_03_02_02 {
    include!(concat!(
        "../03_errors_and_resources/02_exception_propagation_and_matching/rust/",
        "test_02_rethrow_and_completion_precedence.rs"
    ));
}
mod concept_03_03_01 {
    include!(concat!(
        "../03_errors_and_resources/03_error_chaining_suppression_and_aggregation/rust/",
        "test_01_core.rs"
    ));
}
mod concept_03_03_02 {
    include!(concat!(
        "../03_errors_and_resources/03_error_chaining_suppression_and_aggregation/rust/",
        "test_02_multiple_cleanup_failures.rs"
    ));
}
mod concept_03_04_01 {
    include!(concat!(
        "../03_errors_and_resources/04_contracts_assertions_and_failure_signaling/rust/",
        "test_01_core.rs"
    ));
}
mod concept_03_04_02 {
    include!(concat!(
        "../03_errors_and_resources/04_contracts_assertions_and_failure_signaling/rust/",
        "test_02_configuration_and_runtime_boundaries.rs"
    ));
}
mod concept_04_01_01 {
    include!(concat!(
        "../04_collections_and_iteration/01_iteration_protocol/rust/",
        "test_01_core.rs"
    ));
}
mod concept_04_01_02 {
    include!(concat!(
        "../04_collections_and_iteration/01_iteration_protocol/rust/",
        "test_02_iterable_iterator_and_fallbacks.rs"
    ));
}
mod concept_04_02_01 {
    include!(concat!(
        "../04_collections_and_iteration/02_indexing_slicing_and_bounds/rust/",
        "test_01_core.rs"
    ));
}
mod concept_04_03_01 {
    include!(concat!(
        "../04_collections_and_iteration/03_sequence_mutation_and_invalidation/rust/",
        "test_01_core.rs"
    ));
}
mod concept_04_03_02 {
    include!(concat!(
        "../04_collections_and_iteration/03_sequence_mutation_and_invalidation/rust/",
        "test_02_views_and_structural_changes.rs"
    ));
}
mod concept_04_04_01 {
    include!(concat!(
        "../04_collections_and_iteration/04_mapping_lookup_and_missing_keys/rust/",
        "test_01_core.rs"
    ));
}
mod concept_04_05_01 {
    include!(concat!(
        "../04_collections_and_iteration/05_sets_membership_and_deduplication/rust/",
        "test_01_core.rs"
    ));
}
mod concept_04_06_01 {
    include!(concat!(
        "../04_collections_and_iteration/06_generators_laziness_and_early_termination/rust/",
        "test_01_core.rs"
    ));
}
mod concept_04_06_02 {
    include!(concat!(
        "../04_collections_and_iteration/06_generators_laziness_and_early_termination/rust/",
        "test_02_closing_and_delegation.rs"
    ));
}
mod concept_04_07_01 {
    include!(concat!(
        "../04_collections_and_iteration/07_sorting_stability_and_custom_order/rust/",
        "test_01_core.rs"
    ));
}
mod concept_04_07_02 {
    include!(concat!(
        "../04_collections_and_iteration/07_sorting_stability_and_custom_order/rust/",
        "test_02_key_failures_and_comparator_contracts.rs"
    ));
}
mod concept_05_01_01 {
    include!(concat!(
        "../05_objects_and_dispatch/01_construction_initialization_and_lifetime/rust/",
        "test_01_core.rs"
    ));
}
mod concept_05_02_01 {
    include!(concat!(
        "../05_objects_and_dispatch/02_member_attribute_lookup_and_properties/rust/",
        "test_01_core.rs"
    ));
}
mod concept_05_03_01 {
    include!(concat!(
        "../05_objects_and_dispatch/03_inheritance_dynamic_dispatch_and_super/rust/",
        "test_01_core.rs"
    ));
}
mod concept_05_04_01 {
    include!(concat!(
        "../05_objects_and_dispatch/04_encapsulation_private_state_and_immutability/rust/",
        "test_01_core.rs"
    ));
}
mod concept_05_05_01 {
    include!(concat!(
        "../05_objects_and_dispatch/05_operator_and_protocol_customization/rust/",
        "test_01_core.rs"
    ));
}
mod concept_05_06_01 {
    include!(concat!(
        "../05_objects_and_dispatch/06_introspection_reflection_and_runtime_type/rust/",
        "test_01_core.rs"
    ));
}
mod concept_06_01_01 {
    include!(concat!(
        "../06_text_binary_and_serialization/01_unicode_strings_and_code_units/rust/",
        "test_01_core.rs"
    ));
}
mod concept_06_01_02 {
    include!(concat!(
        "../06_text_binary_and_serialization/01_unicode_strings_and_code_units/rust/",
        "test_02_normalization_and_invalid_encoding.rs"
    ));
}
mod concept_06_02_01 {
    include!(concat!(
        "../06_text_binary_and_serialization/02_formatting_parsing_and_interpolation/rust/",
        "test_01_core.rs"
    ));
}
mod concept_06_03_01 {
    include!(concat!(
        "../06_text_binary_and_serialization/03_regular_expressions_and_state/rust/",
        "test_01_core.rs"
    ));
}
mod concept_06_03_02 {
    include!(concat!(
        "../06_text_binary_and_serialization/03_regular_expressions_and_state/rust/",
        "test_02_zero_width_and_failure_boundaries.rs"
    ));
}
mod concept_06_04_01 {
    include!(concat!(
        "../06_text_binary_and_serialization/04_binary_buffers_views_and_endianness/rust/",
        "test_01_core.rs"
    ));
}
mod concept_06_04_02 {
    include!(concat!(
        "../06_text_binary_and_serialization/04_binary_buffers_views_and_endianness/rust/",
        "test_02_alignment_and_lifetime.rs"
    ));
}
mod concept_06_05_01 {
    include!(concat!(
        "../06_text_binary_and_serialization/05_serialization_clone_and_transfer/rust/",
        "test_01_core.rs"
    ));
}
mod concept_06_05_02 {
    include!(concat!(
        "../06_text_binary_and_serialization/05_serialization_clone_and_transfer/rust/",
        "test_02_numeric_and_trust_boundaries.rs"
    ));
}
mod concept_07_01_01 {
    include!(concat!(
        "../07_modules_packages_and_loading/01_modules_imports_linkage_and_live_bindings/rust/",
        "test_01_core.rs"
    ));
}
mod concept_07_01_02 {
    include!(concat!(
        "../07_modules_packages_and_loading/01_modules_imports_linkage_and_live_bindings/rust/",
        "test_02_binding_aliases_and_mutable_exports.rs"
    ));
}
mod concept_07_02_01 {
    include!(concat!(
        "../07_modules_packages_and_loading/02_package_resolution_exports_and_visibility/rust/",
        "test_01_core.rs"
    ));
}
mod concept_07_02_02 {
    include!(concat!(
        "../07_modules_packages_and_loading/02_package_resolution_exports_and_visibility/rust/",
        "test_02_resolution_without_execution.rs"
    ));
}
mod concept_07_03_01 {
    include!(concat!(
        "../07_modules_packages_and_loading/03_initialization_caching_cycles_and_dynamic_loading/rust/",
        "test_01_core.rs"
    ));
}
mod concept_07_03_02 {
    include!(concat!(
        "../07_modules_packages_and_loading/03_initialization_caching_cycles_and_dynamic_loading/rust/",
        "test_02_failed_import_and_cache_state.rs"
    ));
}
mod concept_08_01_01 {
    include!(concat!(
        "../08_async_and_concurrency/01_async_await_and_result_propagation/rust/",
        "test_01_core.rs"
    ));
}
mod concept_08_01_02 {
    include!(concat!(
        "../08_async_and_concurrency/01_async_await_and_result_propagation/rust/",
        "test_02_task_ownership_and_failure_collection.rs"
    ));
}
mod concept_08_02_01 {
    include!(concat!(
        "../08_async_and_concurrency/02_scheduling_tasks_microtasks_and_futures/rust/",
        "test_01_core.rs"
    ));
}
mod concept_08_02_02 {
    include!(concat!(
        "../08_async_and_concurrency/02_scheduling_tasks_microtasks_and_futures/rust/",
        "test_02_ready_queue_boundaries.rs"
    ));
}
mod concept_08_03_01 {
    include!(concat!(
        "../08_async_and_concurrency/03_cancellation_timeouts_and_cleanup/rust/",
        "test_01_core.rs"
    ));
}
mod concept_08_03_02 {
    include!(concat!(
        "../08_async_and_concurrency/03_cancellation_timeouts_and_cleanup/rust/",
        "test_02_timeout_ownership_and_shielding.rs"
    ));
}
mod concept_08_04_01 {
    include!(concat!(
        "../08_async_and_concurrency/04_threads_workers_and_process_isolation/rust/",
        "test_01_core.rs"
    ));
}
mod concept_08_04_02 {
    include!(concat!(
        "../08_async_and_concurrency/04_threads_workers_and_process_isolation/rust/",
        "test_02_result_and_transfer_boundaries.rs"
    ));
}
mod concept_08_05_01 {
    include!(concat!(
        "../08_async_and_concurrency/05_shared_memory_atomics_and_synchronization/rust/",
        "test_01_core.rs"
    ));
}
mod concept_08_05_02 {
    include!(concat!(
        "../08_async_and_concurrency/05_shared_memory_atomics_and_synchronization/rust/",
        "test_02_lost_updates_and_predicates.rs"
    ));
}
mod concept_09_01_01 {
    include!(concat!(
        "../09_files_paths_and_streams/01_path_normalization_and_resolution/rust/",
        "test_01_core.rs"
    ));
}
mod concept_09_02_01 {
    include!(concat!(
        "../09_files_paths_and_streams/02_file_directory_metadata_and_links/rust/",
        "test_01_core.rs"
    ));
}
mod concept_09_03_01 {
    include!(concat!(
        "../09_files_paths_and_streams/03_streaming_buffering_and_backpressure/rust/",
        "test_01_core.rs"
    ));
}
mod concept_09_04_01 {
    include!(concat!(
        "../09_files_paths_and_streams/04_process_environment_and_subprocess_io/rust/",
        "test_01_core.rs"
    ));
}
mod concept_10_01_01 {
    include!(concat!(
        "../10_time_locale_and_runtime/01_durations_clocks_and_monotonic_time/rust/",
        "test_01_core.rs"
    ));
}
mod concept_10_01_02 {
    include!(concat!(
        "../10_time_locale_and_runtime/01_durations_clocks_and_monotonic_time/rust/",
        "test_02_units_and_clock_boundaries.rs"
    ));
}
mod concept_10_02_01 {
    include!(concat!(
        "../10_time_locale_and_runtime/02_calendar_time_zones_and_arithmetic/rust/",
        "test_01_core.rs"
    ));
}
mod concept_10_02_02 {
    include!(concat!(
        "../10_time_locale_and_runtime/02_calendar_time_zones_and_arithmetic/rust/",
        "test_02_transition_and_arithmetic_boundaries.rs"
    ));
}
mod concept_10_03_01 {
    include!(concat!(
        "../10_time_locale_and_runtime/03_locale_numbers_dates_and_collation/rust/",
        "test_01_core.rs"
    ));
}
mod concept_10_03_02 {
    include!(concat!(
        "../10_time_locale_and_runtime/03_locale_numbers_dates_and_collation/rust/",
        "test_02_availability_and_state_boundaries.rs"
    ));
}
mod concept_10_04_01 {
    include!(concat!(
        "../10_time_locale_and_runtime/04_runtime_capabilities_versions_and_feature_detection/rust/",
        "test_01_core.rs"
    ));
}
mod concept_10_04_02 {
    include!(concat!(
        "../10_time_locale_and_runtime/04_runtime_capabilities_versions_and_feature_detection/rust/",
        "test_02_interface_and_implementation_layers.rs"
    ));
}
