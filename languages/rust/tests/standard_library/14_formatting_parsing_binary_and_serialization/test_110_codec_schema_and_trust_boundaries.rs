// polyglot-covers: rust.binary.prefix_validation
// polyglot-covers: rust.serialization.manual_codec_trust

#[derive(Debug, PartialEq)]
struct Record {
    identifier: u16,
    enabled: bool,
}

fn decode_frame(bytes: &[u8], maximum: usize) -> Result<&[u8], &'static str> {
    let prefix: [u8; 2] = bytes.get(..2).ok_or("missing prefix")?.try_into().unwrap();
    let size = u16::from_be_bytes(prefix) as usize;
    if size > maximum {
        return Err("frame too large");
    }
    let payload = bytes.get(2..2 + size).ok_or("truncated payload")?;
    if bytes.len() != 2 + size {
        return Err("trailing data");
    }
    Ok(payload)
}

fn encode_record(record: &Record) -> [u8; 3] {
    let [high, low] = record.identifier.to_be_bytes();
    [high, low, u8::from(record.enabled)]
}

fn decode_record(bytes: &[u8]) -> Result<Record, &'static str> {
    let [high, low, enabled] = *bytes else {
        return Err("record must contain exactly three bytes");
    };
    let enabled = match enabled {
        0 => false,
        1 => true,
        _ => return Err("invalid boolean tag"),
    };
    Ok(Record {
        identifier: u16::from_be_bytes([high, low]),
        enabled,
    })
}

#[test]
fn decoders_validate_all_boundaries_before_allocating_or_trusting_payloads() {
    assert_eq!(decode_frame(&[0, 3, b'r', b's', b't'], 8), Ok(&b"rst"[..]));
    assert_eq!(decode_frame(&[0, 9], 8), Err("frame too large"));
    assert_eq!(decode_frame(&[0, 3, b'r'], 8), Err("truncated payload"));
    assert_eq!(decode_frame(&[0, 1, b'r', b'x'], 8), Err("trailing data"));
}

#[test]
fn a_manual_codec_defines_schema_validation_instead_of_reinterpreting_memory() {
    let record = Record {
        identifier: 513,
        enabled: true,
    };
    assert_eq!(decode_record(&encode_record(&record)), Ok(record));
    assert_eq!(decode_record(&[0, 1, 2]), Err("invalid boolean tag"));
    assert!(decode_record(&[0, 1]).is_err());
}
