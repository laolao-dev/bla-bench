# Sound pan

`calculate_sound_pan(paddle_x, ball_x, screen_width)` returns a signed stereo pan in `[-10000, 10000]`. The ball contributes 18 units per pixel from center; the paddle adds a smaller offset via an arithmetic right shift by two. Both at center produce zero.

REA's JavaScript application analyzer identified `dx-ball-sound-pan.js` as a fully parsed CommonJS module. In `original/dx-ball-sound-pan.js:8`, `calculateSoundPan` computes the center with `screenWidth >> 1`, combines the offsets, and calls `clampPan`. At line 2, `clampPan` saturates the result before using `| 0` to truncate it; line 15 exports both functions. The Python port preserves signed 32-bit coercion before shifts, so a paddle offset of `-1` contributes `-1`, not `0`.
