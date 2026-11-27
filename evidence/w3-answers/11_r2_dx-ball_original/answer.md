# Sound pan calculation

`calculateSoundPan(paddleX, ballX, screenWidth)` returns a signed stereo pan from −10,000 (left) to +10,000 (right). The ball contributes 18 times its horizontal offset from center; the paddle contributes its offset shifted right by two bits. Both at center give zero.

REA’s static JavaScript application analysis identified `dx-ball-sound-pan.js` as a CommonJS module. The export at `original/dx-ball-sound-pan.js:15` names `calculateSoundPan` and its helper, `clampPan`. Lines 8–12 compute the center with `screenWidth >> 1`, then add the ball and paddle contributions. Lines 2–5 clamp the sum before `| 0` converts it to an integer. The Python port preserves the signed 32-bit conversion before each shift, including wraparound and the rounding of negative offsets by arithmetic right shift.
