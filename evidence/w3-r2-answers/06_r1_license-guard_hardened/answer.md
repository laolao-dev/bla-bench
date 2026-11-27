# What the artifact computes

`original/license-validator.js:974` exports `deriveCompositeStreamHak` as
`validateEnterpriseLicense` and `projectLocalCursorR50` as `computeLicenseChecksum`.
The validator is a local prefix and checksum check, not a hardware attestation.

- The corpus digest at line 488 fixes the runtime seed to `3764720783`. The
  cursor routine at line 501 XORs the same mask into both latch words, leaving
  their XOR (low byte `249`) unchanged. Evaluating the string expressions over
  all 1,024 possible length-derived seeds yielded the same strings each time.
- At line 811 the checksum starts at `2166136261` and, for each UTF-16 code unit
  in `license_key + ":" + subject + ":enterprise-v4"`, XORs the unit into the
  accumulator, multiplies by `16777619`, and keeps the low 32 bits.
- At line 878 the validator rejects keys without `ENT-` with `valid: false`
  and tier `none`, omitting the checksum. Otherwise it returns the computed
  checksum and compares it to the supplied unsigned 32-bit value; the tier is
  `enterprise-unlimited` on equality and `invalid` otherwise.

The REA JavaScript application analyzer timed out. The reconstruction uses the
local source and isolated evaluation of its expressions. The Python port models
return values for string inputs and integer checksums, not internal bookkeeping
or arbitrary JavaScript argument coercion.
