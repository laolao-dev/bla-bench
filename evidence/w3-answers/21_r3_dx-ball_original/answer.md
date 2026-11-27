# Stereo sound pan

`calculateSoundPan(paddleX, ballX, screenWidth)` returns an integer stereo pan from −10,000 (left) to +10,000 (right), with zero centered. It computes `center = screenWidth >> 1`, multiplies the ball's offset from center by 18, and adds `(paddleX - center) >> 2`. The paddle therefore has much less influence than the ball.

REA's static JavaScript analysis parsed one file with no parse failures (evidence `ev_73a598115dc5034f7bf2e299da25e15645b659da2fd14a7fd0e0928805119f92`). The formula is visible in `original/dx-ball-sound-pan.js:8`, the clamp and final `| 0` conversion in `original/dx-ball-sound-pan.js:2`, and the exports in `original/dx-ball-sound-pan.js:15`. The Python port preserves signed 32-bit coercion before each shift and clamps before truncating the result toward zero.
