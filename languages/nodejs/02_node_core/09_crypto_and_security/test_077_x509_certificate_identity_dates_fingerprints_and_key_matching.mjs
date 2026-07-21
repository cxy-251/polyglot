// polyglot-covers:
// - nodejs.core.crypto-x509-certificate-pem-der-and-json-representations
// - nodejs.core.crypto-x509-subject-issuer-serial-and-ca
// - nodejs.core.crypto-x509-validity-string-and-date-properties
// - nodejs.core.crypto-x509-fingerprints-and-raw-bytes
// - nodejs.core.crypto-x509-subject-alt-name-host-email-and-ip-checks
// - nodejs.core.crypto-x509-public-key-private-key-match-and-signature-verification
// - nodejs.core.crypto-x509-issued-and-issuer-certificate
// - nodejs.core.crypto-x509-key-usage-and-signature-algorithm
// - nodejs.core.crypto-x509-legacy-object-compatibility
// - nodejs.core.crypto-x509-invalid-input

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  X509Certificate,
  createPrivateKey,
  createPublicKey,
  generateKeyPairSync,
} from 'node:crypto';

// 该证书与私钥只供公开测试：CN/SAN 为 localhost，有效期覆盖 2026-07-21 至
// 2126-06-27。真实系统绝不能复制仓库中的私钥，也不能因为证书能解析就信任它。
const CERTIFICATE_PEM = `-----BEGIN CERTIFICATE-----
MIIBgjCCATSgAwIBAgIUSky+8yr6/CN6kiYLKI7QhMEBF3UwBQYDK2VwMBQxEjAQ
BgNVBAMMCWxvY2FsaG9zdDAgFw0yNjA3MjEyMDEzNDVaGA8yMTI2MDYyNzIwMTM0
NVowFDESMBAGA1UEAwwJbG9jYWxob3N0MCowBQYDK2VwAyEAHLVdVfXte5PBvCZ6
o5riGVo3sJhuwDJN8Qfg1pwx2UmjgZUwgZIwHQYDVR0OBBYEFC7lLpXvKcxStTO0
+fXYKNSYDl6lMB8GA1UdIwQYMBaAFC7lLpXvKcxStTO0+fXYKNSYDl6lMBoGA1Ud
EQQTMBGCCWxvY2FsaG9zdIcEfwAAATAPBgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB
/wQEAwIChDATBgNVHSUEDDAKBggrBgEFBQcDATAFBgMrZXADQQDrnvrch9vOd7sN
VJ9OfymxOXDA7Tq7yQyEcbb03agSwAp0E7muK7SQnb4+G5IbcvF7EGaVar+67N47
/X3sDMkD
-----END CERTIFICATE-----`;

const PRIVATE_KEY_PEM = `-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIFpAGRpwaD6BE9b732kIzmSgwJ7htc1EKbYZgOwOaZ5C
-----END PRIVATE KEY-----`;

test('X509Certificate 接受 PEM，raw 可重建 DER，toString/toJSON 返回 PEM', () => {
  const certificate = new X509Certificate(CERTIFICATE_PEM);
  const fromDer = new X509Certificate(certificate.raw);

  assert.ok(Buffer.isBuffer(certificate.raw));
  assert.notEqual(fromDer.raw, certificate.raw);
  assert.deepEqual(fromDer.raw, certificate.raw);
  assert.equal(certificate.toString(), `${CERTIFICATE_PEM}\n`);
  assert.equal(certificate.toJSON(), certificate.toString());
  assert.equal(JSON.stringify(certificate), JSON.stringify(certificate.toString()));
  // PEM 的结尾换行属于规范化输出的一部分，不应拿原始输入字符串逐字当作身份依据。
});

test('subject、issuer、serialNumber 与 ca 描述证书声明，不等同于已建立信任', () => {
  const certificate = new X509Certificate(CERTIFICATE_PEM);
  assert.equal(certificate.subject, 'CN=localhost');
  assert.equal(certificate.issuer, 'CN=localhost');
  assert.match(certificate.serialNumber, /^[0-9A-F]+$/);
  assert.equal(certificate.ca, true);
  // 自签名且 ca=true 仍不会自动进入 Node 信任库；调用方必须显式建立可信根和验证链。
});

test('validFromDate/validToDate 提供 Date，旧字符串属性保留 OpenSSL 格式', () => {
  const certificate = new X509Certificate(CERTIFICATE_PEM);
  assert.ok(certificate.validFromDate instanceof Date);
  assert.ok(certificate.validToDate instanceof Date);
  assert.ok(certificate.validFromDate < certificate.validToDate);
  assert.equal(certificate.validFromDate.getUTCFullYear(), 2026);
  assert.equal(certificate.validToDate.getUTCFullYear(), 2126);
  assert.equal(typeof certificate.validFrom, 'string');
  assert.equal(typeof certificate.validTo, 'string');
});

test('fingerprint 系列使用不同摘要，raw 是原始 DER 字节', () => {
  const certificate = new X509Certificate(CERTIFICATE_PEM);
  assert.match(certificate.fingerprint, /^(?:[0-9A-F]{2}:){19}[0-9A-F]{2}$/);
  assert.match(certificate.fingerprint256, /^(?:[0-9A-F]{2}:){31}[0-9A-F]{2}$/);
  assert.match(certificate.fingerprint512, /^(?:[0-9A-F]{2}:){63}[0-9A-F]{2}$/);
  assert.notEqual(certificate.fingerprint, certificate.fingerprint256);
  assert.ok(certificate.raw.length > 0);
  // 指纹适合与可信配置做精确绑定；显示给人比较时仍要明确所用摘要和完整值。
});

test('checkHost/checkIP 根据 SAN 返回匹配名，失败返回 undefined 而不抛错', () => {
  const certificate = new X509Certificate(CERTIFICATE_PEM);
  assert.match(certificate.subjectAltName, /DNS:localhost/);
  assert.match(certificate.subjectAltName, /IP Address:127\.0\.0\.1/);
  assert.equal(certificate.checkHost('localhost'), 'localhost');
  assert.equal(certificate.checkIP('127.0.0.1'), '127.0.0.1');
  assert.equal(certificate.checkHost('wrong.example'), undefined);
  assert.equal(certificate.checkIP('127.0.0.2'), undefined);
  assert.equal(certificate.checkEmail('user@localhost'), undefined);
});

test('publicKey、checkPrivateKey 与 verify 分别检查密钥匹配和证书签名', () => {
  const certificate = new X509Certificate(CERTIFICATE_PEM);
  const privateKey = createPrivateKey(PRIVATE_KEY_PEM);
  const otherPrivateKey = generateKeyPairSync('ed25519').privateKey;

  assert.equal(certificate.publicKey.type, 'public');
  assert.equal(certificate.publicKey.asymmetricKeyType, 'ed25519');
  assert.equal(certificate.checkPrivateKey(privateKey), true);
  assert.equal(certificate.checkPrivateKey(otherPrivateKey), false);
  assert.equal(certificate.verify(certificate.publicKey), true);
  assert.equal(createPublicKey(privateKey).equals(certificate.publicKey), true);
  assert.equal(certificate.verify(createPublicKey(otherPrivateKey)), false);
});

test('checkIssued 判断签发关系，独立构造时不会凭 issuer 名称虚构证书链', () => {
  const certificate = new X509Certificate(CERTIFICATE_PEM);
  assert.equal(certificate.checkIssued(certificate), true);
  assert.equal(certificate.issuerCertificate, undefined);
  // issuerCertificate 需要输入中带有可解析链关系；subject/issuer 文本相同不足以补出对象。
});

test('keyUsage 与 signatureAlgorithm 暴露扩展用途和签名算法 OID', () => {
  const certificate = new X509Certificate(CERTIFICATE_PEM);
  assert.deepEqual(certificate.keyUsage, ['1.3.6.1.5.5.7.3.1']);
  assert.match(certificate.signatureAlgorithm, /ed25519/i);
  assert.equal(certificate.signatureAlgorithmOid, '1.3.101.112');
  assert.equal(certificate.infoAccess, undefined);
  // keyUsage 这里只报告 Extended Key Usage OID；它不是授权业务权限的通用角色字段。
});

test('toLegacyObject 为旧 TLS 代码提供兼容形状，新代码优先使用强类型属性', () => {
  const certificate = new X509Certificate(CERTIFICATE_PEM);
  const legacy = certificate.toLegacyObject();
  assert.equal(legacy.subject.CN, 'localhost');
  assert.equal(legacy.issuer.CN, 'localhost');
  assert.match(legacy.subjectaltname, /DNS:localhost/);
  assert.deepEqual(legacy.ext_key_usage, ['1.3.6.1.5.5.7.3.1']);
  assert.equal(legacy.fingerprint256, certificate.fingerprint256);
  assert.ok(Buffer.isBuffer(legacy.raw));
});

test('无法解析的输入在构造阶段失败，不会得到部分初始化证书', () => {
  assert.throws(
    () => new X509Certificate('not a certificate'),
    (error) => error.code === 'ERR_OSSL_PEM_NO_START_LINE',
  );
});
