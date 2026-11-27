
function clampPan(panValue) {
  if (panValue < -10000) return -10000;
  if (panValue > 10000) return 10000;
  return panValue | 0;
}

function calculateSoundPan(paddleX, ballX, screenWidth) {
  const center = screenWidth >> 1;
  const delta = (ballX - center) * 18;
  const weighted = delta + ((paddleX - center) >> 2);
  return clampPan(weighted);
}

module.exports = { calculateSoundPan, clampPan };
