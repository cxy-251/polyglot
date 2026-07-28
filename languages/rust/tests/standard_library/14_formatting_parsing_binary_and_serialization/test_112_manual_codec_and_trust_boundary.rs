// polyglot-covers: rust.serialization.manual_codec_trust

#[derive(Debug, PartialEq)]
struct Record {
    identifier: u16,
    enabled: bool,
}

fn encode(record: &Record) -> [u8; 3] {
    let [high, low] = record.identifier.to_be_bytes();
    [high, low, u8::from(record.enabled)]
}

fn decode(bytes: &[u8]) -> Result<Record, &'static str> {
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
fn a_manual_codec_must_define_schema_validation_and_aliasing_semantics() {
    let record = Record {
        identifier: 513,
        enabled: true,
    };
    assert_eq!(decode(&encode(&record)), Ok(record));
    assert_eq!(decode(&[0, 1, 2]), Err("invalid boolean tag"));
    assert_eq!(
        decode(&[0, 1]),
        Err("record must contain exactly three bytes")
    );
}
