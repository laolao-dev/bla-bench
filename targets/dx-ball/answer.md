# DX-Ball sound pan

For numeric inputs, `calculate_sound_pan(paddle_x, ball_x, screen_width)` returns an integer stereo pan in `[-10000, 10000]`. It computes the center as `screenWidth >> 1`, multiplies the ball's horizontal offset from center by 18, and adds the paddle's horizontal offset shifted right by two. Both shifts use JavaScript signed 32-bit conversion.

REA static analysis (`ev_6e070f1e010637b17fbe9145f1f6f0d63be0cfdda6abc453a8f298cdc4317d60`) identified a parsed CommonJS asset whose SHA-256 matched the local file. `original/dx-ball-sound-pan.js:8` defines the formula, line 2 defines the clamp and final `| 0` integer conversion, and line 15 exports both functions. The artifact was not executed.
