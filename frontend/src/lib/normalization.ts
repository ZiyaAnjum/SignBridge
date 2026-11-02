/**
 * Canonical landmark normalization module for SignBridge.
 * Shared logic mirroring ml-service/app/core/normalization.py.
 * Spec defined in docs/LANDMARKS.md.
 */

export const POSE_START = 0;
export const POSE_END = 99; // 33 * 3
export const LEFT_HAND_START = 99;
export const LEFT_HAND_END = 162; // 21 * 3
export const RIGHT_HAND_START = 162;
export const RIGHT_HAND_END = 225; // 21 * 3

export const LEFT_SHOULDER_IDX = 11;
export const RIGHT_SHOULDER_IDX = 12;
export const MIN_SHOULDER_WIDTH = 0.05;
export const DEFAULT_ASPECT_RATIO = 16.0 / 9.0;

export interface Anchor {
  mx: number;
  my: number;
  mz: number;
  scale: number;
}

export function isHandDetected(slice: Float32Array | number[]): boolean {
  for (let i = 0; i < slice.length; i++) {
    if (slice[i] !== 0.0) return true;
  }
  return false;
}

export function computeShoulderAnchor(
  frame: Float32Array | number[],
  aspectRatio: number = DEFAULT_ASPECT_RATIO,
  lastAnchor: Anchor | null = null,
): { anchor: Anchor; isValid: boolean } {
  const lsX = frame[LEFT_SHOULDER_IDX * 3];
  const lsY = frame[LEFT_SHOULDER_IDX * 3 + 1];
  const lsZ = frame[LEFT_SHOULDER_IDX * 3 + 2];

  const rsX = frame[RIGHT_SHOULDER_IDX * 3];
  const rsY = frame[RIGHT_SHOULDER_IDX * 3 + 1];
  const rsZ = frame[RIGHT_SHOULDER_IDX * 3 + 2];

  const lsMissing = lsX === 0.0 && lsY === 0.0 && lsZ === 0.0;
  const rsMissing = rsX === 0.0 && rsY === 0.0 && rsZ === 0.0;

  if (lsMissing || rsMissing) {
    if (lastAnchor !== null) {
      return { anchor: lastAnchor, isValid: false };
    }
    return {
      anchor: { mx: 0.5 * aspectRatio, my: 0.5, mz: 0.0, scale: 1.0 },
      isValid: false,
    };
  }

  const lsXAspect = lsX * aspectRatio;
  const rsXAspect = rsX * aspectRatio;

  const dx = lsXAspect - rsXAspect;
  const dy = lsY - rsY;
  const dz = lsZ - rsZ;
  const scale = Math.sqrt(dx * dx + dy * dy + dz * dz);

  if (scale < MIN_SHOULDER_WIDTH) {
    if (lastAnchor !== null) {
      return { anchor: lastAnchor, isValid: false };
    }
    return {
      anchor: { mx: 0.5 * aspectRatio, my: 0.5, mz: 0.0, scale: 1.0 },
      isValid: false,
    };
  }

  const mx = (lsXAspect + rsXAspect) / 2.0;
  const my = (lsY + rsY) / 2.0;
  const mz = (lsZ + rsZ) / 2.0;

  return { anchor: { mx, my, mz, scale }, isValid: true };
}

export function normalizeFrame(
  frame: Float32Array | number[],
  aspectRatio: number = DEFAULT_ASPECT_RATIO,
  lastAnchor: Anchor | null = null,
): { normalized: Float32Array; anchor: Anchor } {
  if (frame.length !== 225) {
    throw new Error(`Expected frame length 225, got ${frame.length}`);
  }

  const { anchor } = computeShoulderAnchor(frame, aspectRatio, lastAnchor);
  const out = new Float32Array(225);

  // 1. Pose landmarks (indices 0..98)
  for (let i = 0; i < 33; i++) {
    const idx = i * 3;
    const x = frame[idx];
    const y = frame[idx + 1];
    const z = frame[idx + 2];
    if (x !== 0.0 || y !== 0.0 || z !== 0.0) {
      out[idx] = (x * aspectRatio - anchor.mx) / anchor.scale;
      out[idx + 1] = (y - anchor.my) / anchor.scale;
      out[idx + 2] = (z - anchor.mz) / anchor.scale;
    }
  }

  // 2. Left Hand (indices 99..161) ONLY if detected
  const lhSlice = frame.slice(LEFT_HAND_START, LEFT_HAND_END);
  if (isHandDetected(lhSlice)) {
    for (let i = 0; i < 21; i++) {
      const idx = LEFT_HAND_START + i * 3;
      const x = frame[idx];
      const y = frame[idx + 1];
      const z = frame[idx + 2];
      out[idx] = (x * aspectRatio - anchor.mx) / anchor.scale;
      out[idx + 1] = (y - anchor.my) / anchor.scale;
      out[idx + 2] = (z - anchor.mz) / anchor.scale;
    }
  }

  // 3. Right Hand (indices 162..224) ONLY if detected
  const rhSlice = frame.slice(RIGHT_HAND_START, RIGHT_HAND_END);
  if (isHandDetected(rhSlice)) {
    for (let i = 0; i < 21; i++) {
      const idx = RIGHT_HAND_START + i * 3;
      const x = frame[idx];
      const y = frame[idx + 1];
      const z = frame[idx + 2];
      out[idx] = (x * aspectRatio - anchor.mx) / anchor.scale;
      out[idx + 1] = (y - anchor.my) / anchor.scale;
      out[idx + 2] = (z - anchor.mz) / anchor.scale;
    }
  }

  return { normalized: out, anchor };
}

export function normalizeSequence(
  sequence: Array<Float32Array | number[]>,
  aspectRatio: number = DEFAULT_ASPECT_RATIO,
): Float32Array[] {
  let anchor: Anchor | null = null;
  return sequence.map((frame) => {
    const result = normalizeFrame(frame, aspectRatio, anchor);
    anchor = result.anchor;
    return result.normalized;
  });
}

