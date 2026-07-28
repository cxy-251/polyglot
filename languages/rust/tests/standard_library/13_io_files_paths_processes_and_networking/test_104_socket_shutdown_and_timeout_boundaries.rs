// polyglot-covers: rust.io.socket_shutdown_timeout

use std::io::{Read, Write};
use std::net::{Ipv4Addr, Shutdown, TcpListener, TcpStream};
use std::time::Duration;

#[test]
fn shutdown_write_delivers_eof_and_timeouts_are_deadlock_guards() {
    let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0)).unwrap();
    let address = listener.local_addr().unwrap();
    let server = std::thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        stream
            .set_read_timeout(Some(Duration::from_secs(5)))
            .unwrap();
        let mut request = Vec::new();
        stream.read_to_end(&mut request).unwrap();
        request
    });
    let mut client = TcpStream::connect(address).unwrap();
    client.write_all(b"complete request").unwrap();
    client.shutdown(Shutdown::Write).unwrap();
    assert_eq!(server.join().unwrap(), b"complete request");
}
