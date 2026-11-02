/**
 * TypeScript parity test suite for landmark normalization.
 * Tests:
 * 1. Standard full pose + two hands.
 * 2. Missing-hand case: undetected hand must remain exactly 0.0.
 * 3. Missing-shoulder case: degenerate shoulder width fallback.
 * 4. Aspect ratio scaling verification.
 */

import {
  normalizeFrame,
  normalizeSequence,
  LEFT_HAND_START,
  LEFT_HAND_END,
  RIGHT_HAND_START,
  RIGHT_HAND_END,
  LEFT_SHOULDER_IDX,
  RIGHT_SHOULDER_IDX,
} from './normalization';

function createSyntheticFrame(
  ls = [0.4, 0.4, 0.1],
  rs = [0.6, 0.4, 0.1],
  lhPresent = true,
  rhPresent = true,
): Float32Array {
  const frame = new Float32Array(225);

  // Set shoulders
  frame[LEFT_SHOULDER_IDX * 3] = ls[0];
  frame[LEFT_SHOULDER_IDX * 3 + 1] = ls[1];
  frame[LEFT_SHOULDER_IDX * 3 + 2] = ls[2];

  frame[RIGHT_SHOULDER_IDX * 3] = rs[0];
  frame[RIGHT_SHOULDER_IDX * 3 + 1] = rs[1];
  frame[RIGHT_SHOULDER_IDX * 3 + 2] = rs[2];

  // Nose
  frame[0] = 0.5;
  frame[1] = 0.2;
  frame[2] = 0.0;

  if (lhPresent) {
    for (let i = 0; i < 21; i++) {
      frame[LEFT_HAND_START + i * 3] = 0.3;
      frame[LEFT_HAND_START + i * 3 + 1] = 0.5;
      frame[LEFT_HAND_START + i * 3 + 2] = 0.0;
    }
  }

  if (rhPresent) {
    for (let i = 0; i < 21; i++) {
      frame[RIGHT_HAND_START + i * 3] = 0.7;
      frame[RIGHT_HAND_START + i * 3 + 1] = 0.5;
      frame[RIGHT_HAND_START + i * 3 + 2] = 0.0;
    }
  }

  return frame;
}

export function runNormalizationParityTests(): boolean {
  const aspect = 16.0 / 9.0;

  // Test 1: Standard normalization
  const f1 = createSyntheticFrame([0.4, 0.4, 0.0], [0.6, 0.4, 0.0], true, true);
  const { normalized: norm1, anchor: a1 } = normalizeFrame(f1, aspect);
  const expectedScale = (0.6 - 0.4) * aspect;
  if (Math.abs(a1.scale - expectedScale) > 1e-5) {
    throw new Error(`Scale mismatch: expected ${expectedScale}, got ${a1.scale}`);
  }
  const lsNormX = norm1[LEFT_SHOULDER_IDX * 3];
  const rsNormX = norm1[RIGHT_SHOULDER_IDX * 3];
  if (Math.abs(lsNormX - -0.5) > 1e-4 || Math.abs(rsNormX - 0.5) > 1e-4) {
    throw new Error(`Shoulder coordinate mismatch: ${lsNormX}, ${rsNormX}`);
  }

  // Test 2: Missing hand case
  const f2 = createSyntheticFrame([0.4, 0.4, 0.0], [0.6, 0.4, 0.0], true, false);
  const { normalized: norm2 } = normalizeFrame(f2, aspect);
  for (let i = RIGHT_HAND_START; i < RIGHT_HAND_END; i++) {
    if (norm2[i] !== 0.0) {
      throw new Error(`Right hand coordinate at index ${i} was not zero: ${norm2[i]}`);
    }
  }

  // Test 3: Missing shoulder fallback
  const f3Missing = createSyntheticFrame([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]);
  const { anchor: aFallback } = normalizeFrame(f3Missing, aspect, a1);
  if (aFallback.scale !== a1.scale || aFallback.mx !== a1.mx) {
    throw new Error('Failed to reuse prior anchor on missing shoulders');
  }

  const { anchor: aNeutral } = normalizeFrame(f3Missing, aspect, null);
  if (aNeutral.scale !== 1.0 || Math.abs(aNeutral.mx - 0.5 * aspect) > 1e-5) {
    throw new Error('Failed to use neutral fallback on missing shoulders');
  }

  // Test 4: Sequence normalization
  const seq = Array.from({ length: 30 }, (_, idx) =>
    idx === 0
      ? createSyntheticFrame([0.4, 0.4, 0.0], [0.6, 0.4, 0.0])
      : createSyntheticFrame([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]),
  );
  const normSeq = normalizeSequence(seq, aspect);
  if (normSeq.length !== 30) throw new Error('Sequence length mismatch');

  console.log('All TypeScript normalization parity tests passed!');
  return true;
}


runNormalizationParityTests();
