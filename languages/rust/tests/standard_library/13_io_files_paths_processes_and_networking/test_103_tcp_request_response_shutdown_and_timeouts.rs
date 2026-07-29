// polyglot-covers: rust.io.tcp_loopback_request_response
// polyglot-covers: rust.io.socket_shutdown_timeout

use std::io::{Read, Write};
use std::net::{Ipv4Addr, Shutdown, TcpListener, TcpStream};
use std::time::Duration;

#[test]
fn tcp_loopback_uses_a_dynamic_port_and_explicit_request_response_protocol() {
    let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0)).unwrap();
    let address = listener.local_addr().unwrap();
    let server = std::thread::spawn(move || {
        let (mut stream, peer) = listener.accept().unwrap();
        assert!(peer.ip().is_loopback());
        let mut request = [0; 4];
        stream.read_exact(&mut request).unwrap();
        assert_eq!(&request, b"ping");
        stream.write_all(b"pong").unwrap();
    });
    let mut client = TcpStream::connect(address).unwrap();
    client.write_all(b"ping").unwrap();
    let mut response = [0; 4];
    client.read_exact(&mut response).unwrap();
    assert_eq!(&response, b"pong");
    server.join().unwrap();
}

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
