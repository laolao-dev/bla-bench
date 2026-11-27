# DX-Ball sound pan

The main export, `calculateSoundPan`, computes a signed stereo pan value. It sets `center = ToInt32(third) >> 1` and computes `18 * (second - center) + (ToInt32(first - center) >> 2)`. It clamps the result to `[-10000, 10000]` and truncates in-range values toward zero. The Python equivalent covers numeric inputs.

`original/dx-ball-sound-pan.js:918` maps the exports to the bodies at lines 862 and 805. The runtime seed has low three bits `001`, and the input-dependent part starts at bit 8. Thus each square-and-mask predicate evaluates to `1` before comparison, selecting the arithmetic constants `18` and `10000` and skipping the extra conditional calls. The unconditional cursor updates do not feed the returned value.

REA's static JavaScript application analysis timed out. I traced the shipped source directly and checked the exports in Node: `(640, 320, 640)` returns `80`, `(0, 0, 640)` returns `-5840`, and the clamp saturates at both endpoints.
