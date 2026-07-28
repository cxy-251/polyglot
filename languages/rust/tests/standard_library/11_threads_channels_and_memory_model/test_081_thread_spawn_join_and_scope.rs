// polyglot-covers: rust.concurrency.thread_spawn_join_scope

#[test]
fn join_returns_owned_results_and_scope_allows_borrowed_thread_inputs() {
    let handle = std::thread::spawn(|| (1..=6).product::<i32>());
    assert_eq!(handle.join().unwrap(), 720);

    let values = [2, 3, 5, 7];
    let totals = std::thread::scope(|scope| {
        let left = scope.spawn(|| values[..2].iter().sum::<i32>());
        let right = scope.spawn(|| values[2..].iter().sum::<i32>());
        (left.join().unwrap(), right.join().unwrap())
    });
    assert_eq!(totals, (5, 12));
}
