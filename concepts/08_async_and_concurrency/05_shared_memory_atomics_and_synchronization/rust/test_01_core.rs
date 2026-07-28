// polyglot-family: async_and_concurrency
// polyglot-concept: shared_memory_atomics_and_synchronization
// polyglot-related: languages/rust/tests/standard_library/
// polyglot-related+: 11_threads_channels_and_memory_model/test_086_atomics_ordering_and_happens_before.rs
//
// 共同问题：共享读写如何同步；atomic、lock 与消息传递分别保证什么。
// 对照观察：Send/Sync gate sharing；atomic orders individual state，Mutex protects compound invariants，channel transfers values.

use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, mpsc};

#[test]
fn comparison() {
    let atomic = AtomicUsize::new(1);
    assert_eq!(atomic.fetch_add(1, Ordering::SeqCst), 1);
    assert_eq!(atomic.load(Ordering::SeqCst), 2);

    let pair = Arc::new(Mutex::new((0, 0)));
    let worker_pair = Arc::clone(&pair);
    let (sender, receiver) = mpsc::channel();
    std::thread::spawn(move || {
        *worker_pair.lock().unwrap() = (20, 22);
        sender.send("done").unwrap();
    });
    assert_eq!(receiver.recv().unwrap(), "done");
    assert_eq!(*pair.lock().unwrap(), (20, 22));
}
