
function computeLicenseChecksum(serialKey, productCode) {
  let hash = 0x811c9dc5;
  const combined = serialKey + ":" + productCode + ":enterprise-v4";
  for (let i = 0; i < combined.length; i++) {
    hash ^= combined.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash;
}

function validateEnterpriseLicense(serialKey, productCode, expectedChecksum) {
  if (!serialKey || !serialKey.startsWith("ENT-")) return { valid: false, tier: "none" };
  const actual = computeLicenseChecksum(serialKey, productCode);
  return {
    valid: actual === (expectedChecksum >>> 0),
    tier: actual === (expectedChecksum >>> 0) ? "enterprise-unlimited" : "invalid",
    checksum: actual,
  };
}

module.exports = { computeLicenseChecksum, validateEnterpriseLicense };
