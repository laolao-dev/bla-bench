# DX-Ball sound pan

`calculateSoundPan` computes a signed stereo pan between −10,000 (left) and +10,000 (right). It shifts the third argument right by one to find the center, weights the second argument's displacement from center by 18, and adds the first argument's displacement shifted right by two. It clamps the result and truncates any in-range fraction toward zero.

The CommonJS export at `original/dx-ball-sound-pan.js:918` points to the calculation at line 862 and the clamp at line 805. The runtime seed is odd and the per-input mix changes only bits 8 and above. The branch XOR masks are multiples of four, so the squared seeds are always 1 modulo 8. This rules out the conditional state calls and selects `Math.imul` expressions that reduce to 18 and 10,000. The remaining state updates do not change the seed or affect the returned pan.

REA's application analysis timed out; the reconstruction uses direct source inspection and local Node comparisons. The Python port preserves JavaScript's signed 32-bit shifts for numeric inputs.
