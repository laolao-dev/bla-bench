# DX-Ball sound pan

`calculateSoundPan(x, sound_x, width)` returns an integer stereo pan in
`[-10000, 10000]`. It takes the signed 32-bit half-width as the center,
weights the second coordinate's offset by 18, and adds the first
coordinate's offset shifted right by two. Negative values pan left,
positive values pan right, and two centered coordinates give zero.

REA identified the artifact as JavaScript; its application-graph analysis
timed out. The CommonJS export at `original/dx-ball-sound-pan.js:918` points
to the arithmetic at line 862 and the clamp at line 805. The corpus digest
evaluates to `1670421233`, giving the initialized seed a low three-bit
value of `1`. Input-dependent seed terms start at bit 8, so they cannot
change the branch tests masked with `& 7`. Evaluating the selected
`Math.imul` expressions gives the multiplier `18` and both clamp
magnitudes `10000`. The Python port preserves JavaScript's signed
32-bit conversion and arithmetic right shifts for numeric inputs.
