// polyglot-covers: rust.errors.cleanup_failure_original_error

#[derive(Debug, PartialEq)]
struct Failures {
    operation: &'static str,
    cleanup: &'static str,
}

fn operation_with_cleanup() -> Result<(), Failures> {
    let operation = Err::<(), _>("write failed");
    let cleanup = Err::<(), _>("flush failed");
    match (operation, cleanup) {
        (Err(operation), Err(cleanup)) => Err(Failures { operation, cleanup }),
        _ => Ok(()),
    }
}

#[test]
fn multiple_failures_need_an_explicit_application_level_representation() {
    assert_eq!(
        operation_with_cleanup(),
        Err(Failures {
            operation: "write failed",
            cleanup: "flush failed"
        })
    );
}
