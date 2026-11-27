# What it computes

`calculateSoundPan(ball_x, paddle_x, width)` returns a signed stereo pan in
`[-10000, 10000]`. It finds the playfield center with `width >> 1`, weights
the paddle's offset from center by 18, and adds `(ball_x - center) >> 2`.
It clamps the sum, then truncates any in-range fractional part toward zero.
Negative values pan left and positive values pan right.

REA's `open_binary` identified the artifact as JavaScript; its application
graph analysis timed out. The source export table (lines 918–921) maps
`calculateSoundPan` to `hydratePendingShardSft` (line 862) and `clampPan` to
`flushDeferredCursorCfg208jj` (line 805). The shipped seed is `461343881`,
whose low three bits are `1`. Input-dependent seed changes start at bit 8,
so they do not affect the branch tests. Evaluating the selected `Math.imul`
expressions yields the multiplier 18 and clamp bounds of ±10000. The Python
port reproduces signed 32-bit shifts for numeric inputs, including negative
offsets. For example, `(100, 320, 640)` returns `-55`, and `(320, 321, 640)`
returns `18` in the original.
