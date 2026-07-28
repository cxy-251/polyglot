// polyglot-covers: rust.concurrency.channels_sync_backpressure

use std::sync::mpsc::{self, TrySendError};

#[test]
fn channels_transfer_ownership_and_sync_channel_exposes_capacity() {
    let (sender, receiver) = mpsc::channel();
    sender.send(String::from("owned")).unwrap();
    drop(sender);
    assert_eq!(receiver.recv().unwrap(), "owned");
    assert!(receiver.recv().is_err());

    let (sender, receiver) = mpsc::sync_channel(1);
    sender.try_send(1).unwrap();
    assert_eq!(sender.try_send(2), Err(TrySendError::Full(2)));
    assert_eq!(receiver.recv().unwrap(), 1);
    sender.try_send(2).unwrap();
    assert_eq!(receiver.recv().unwrap(), 2);
}
