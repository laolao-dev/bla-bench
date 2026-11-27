# DX-Ball stereo pan

REA's `analyze_javascript_application` parsed the single JavaScript artifact without executing it. The source at `original/dx-ball-sound-pan.js:8` shows that `calculateSoundPan` takes `screenWidth >> 1` as the center, multiplies the ball's horizontal offset by 18, and adds the paddle's horizontal offset shifted right by two. Negative values pan left, positive values pan right, and zero is centered.

The helper at `original/dx-ball-sound-pan.js:2` clamps the result to −10,000 through +10,000 and uses `| 0` on the unclamped path. The Python translation preserves JavaScript's signed 32-bit conversions, including arithmetic right shifts and truncation toward zero on the final conversion.
